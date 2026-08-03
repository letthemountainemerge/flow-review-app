"""
基于 LLM 视觉能力的图片流程图解析器

将流程图图片发送给多模态大模型，让其识别节点、连线、泳道等结构化信息
"""
import json
import os
import re
import logging
from typing import List, Optional

from app.models.schemas import (
    ParsedDocument, FlowNode, FlowEdge, Swimlane, ParseError
)
from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一位专业的 BPMN 流程图解析专家。请仔细分析用户上传的流程图图片，识别出所有流程元素并以严格的 JSON 格式返回。

输出 JSON 格式要求：
{
  "nodes": [
    {
      "id": "唯一标识符（如 n1, n2, 用简短英文）",
      "name": "节点显示的文字",
      "node_type": "节点类型",
      "lane_id": "所属泳道id（如果不在任何泳道则为空字符串）",
      "is_kcp": false
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "源节点id",
      "target": "目标节点id",
      "name": "连线上标注的条件文字（如 是/否/合格/不合格），没有则为空字符串"
    }
  ],
  "swimlanes": [
    {
      "id": "lane1",
      "name": "泳道名称（如 生产计划员、检验员）",
      "node_ids": ["属于该泳道的节点id列表"]
    }
  ],
  "kcp_nodes": ["被标记为关键控制点的节点id列表"]
}

节点类型（node_type）必须使用以下之一：
- startEvent: 开始节点（圆形，通常无文字或标"开始"）
- endEvent: 结束节点（圆形，通常标"结束"）  
- task: 任务/活动节点（矩形或圆角矩形）
- exclusiveGateway: 排他网关/判断节点（菱形，通常有 是/否 等条件分支）
- parallelGateway: 并行网关（加号菱形）
- subprocess: 子流程（双层矩形）
- dataObject: 数据对象

重要规则：
1. 必须识别出流程图中的开始节点和结束节点
2. 泳道（横向或纵向的分区，带有角色/部门名称）必须完整识别
3. 判断节点（菱形）要标注为 exclusiveGateway
4. 连线要按实际箭头方向标注 source -> target
5. 连线上如果有条件文字（如 是、否、合格、不合格），要放入 name 字段
6. 如果节点上标注了 "KCP" 或 "关键控制点" 等字样，将 is_kcp 设为 true
7. 只返回 JSON，不要有任何其他文字说明
"""


def _extract_json(text: str) -> Optional[dict]:
    """从 LLM 输出中提取 JSON"""
    # 尝试直接解析
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except Exception:
            pass

    # 尝试提取 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 尝试提取最外层 {}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            pass

    return None


class ImageLLMParser:
    """基于 LLM 视觉能力的图片解析器"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> ParsedDocument:
        """解析图片流程图"""
        file_name = os.path.basename(self.file_path)

        if not os.path.exists(self.file_path):
            return ParsedDocument(
                file_type="image",
                file_name=file_name,
                errors=[ParseError(type="file_not_found", message="文件不存在")],
            )

        try:
            llm = get_llm_client()
            logger.info(f"ImageLLMParser: 开始解析图片 {file_name}, 模型={llm.model}")

            # 两步策略：Token Plan 个人版视觉+结构化JSON超时严重
            # Step 1: 快速视觉描述（简单prompt，~5s）
            step1_prompt = (
                "请仔细观察这张流程图，用文字详细描述以下内容：\n"
                "1. 每个泳道（角色/部门）的名称\n"
                "2. 每个节点的文字内容、形状（矩形/菱形/圆形）\n"
                "3. 节点之间的连线方向和条件文字（如 是/否）\n"
                "4. 哪些是开始和结束节点\n"
            )
            desc = llm.chat_with_image(
                system_prompt="你是一位流程图分析助手，请用中文描述图片内容。",
                user_prompt=step1_prompt,
                image_path=self.file_path,
                temperature=0.0,
                max_tokens=2000,
            )
            logger.info(f"ImageLLMParser: Step1 描述完成, {len(desc)} 字符")

            # Step 2: 纯文本结构化（不需要图片，快）
            step2_prompt = (
                f"根据以下流程图描述，生成严格的JSON格式数据：\n\n{desc}\n\n"
                + SYSTEM_PROMPT.replace("请仔细分析用户上传的流程图图片，识别出所有流程元素并以严格的 JSON 格式返回。",
                                         "请根据上述描述生成严格的JSON格式数据。")
            )
            raw = llm.chat(
                system_prompt=step2_prompt,
                user_prompt="请按照系统提示，输出JSON。只输出JSON，不要其他文字。",
                temperature=0.0,
                max_tokens=4000,
            )
            logger.info(f"ImageLLMParser: Step2 JSON完成, {len(raw)} 字符")
        except Exception as e:
            err_msg = str(e)
            err_type = type(e).__name__
            logger.error(f"ImageLLMParser: LLM调用异常! type={err_type}, msg={err_msg}", exc_info=True)
            # 识别 400 错误 — 通常表示模型不支持图片输入
            if "400" in err_msg or "image_url" in err_msg or "unsupported" in err_msg.lower():
                return ParsedDocument(
                    file_type="image",
                    file_name=file_name,
                    errors=[ParseError(
                        type="model_unsupported",
                        message=f"当前模型 {get_llm_client().model} 不支持图片输入，无法解析流程图。"
                                f"请使用多模态视觉模型（如 qwen-vl-max、doubao-seed-2.0-pro 等）。"
                    )],
                )
            return ParsedDocument(
                file_type="image",
                file_name=file_name,
                errors=[ParseError(type="llm_error", message=f"LLM 调用失败: {err_msg}")],
            )

        data = _extract_json(raw)
        if data is None:
            return ParsedDocument(
                file_type="image",
                file_name=file_name,
                errors=[ParseError(type="parse_error", message="LLM 返回格式无法解析", suggestion=raw[:500])],
            )

        nodes: List[FlowNode] = []
        edges: List[FlowEdge] = []
        swimlanes: List[Swimlane] = []
        kcp_nodes: List[str] = []

        # 解析 nodes
        for n in data.get("nodes", []):
            try:
                node = FlowNode(
                    id=n.get("id", ""),
                    name=n.get("name", ""),
                    node_type=n.get("node_type", "task"),
                    lane_id=n.get("lane_id") or None,
                    outgoing=n.get("outgoing", []),
                    incoming=n.get("incoming", []),
                    is_kcp=n.get("is_kcp", False),
                    documentation=n.get("documentation", ""),
                )
                nodes.append(node)
            except Exception:
                continue

        # 解析 edges
        for e in data.get("edges", []):
            try:
                edge = FlowEdge(
                    id=e.get("id", ""),
                    source=e.get("source", ""),
                    target=e.get("target", ""),
                    name=e.get("name") or None,
                )
                edges.append(edge)
            except Exception:
                continue

        # 解析 swimlanes
        for s in data.get("swimlanes", []):
            try:
                lane = Swimlane(
                    id=s.get("id", ""),
                    name=s.get("name", ""),
                    node_ids=s.get("node_ids", []),
                )
                swimlanes.append(lane)
            except Exception:
                continue

        # KCP 节点
        kcp_nodes = data.get("kcp_nodes", [])

        warnings = []
        if not nodes:
            warnings.append("LLM 未能识别出任何流程节点")
        if not swimlanes:
            warnings.append("LLM 未能识别出任何泳道")

        # 如果 LLM 没识别到泳道，但图片里明显有泳道，这算是一个警告
        # 不过不强制，因为有些图确实没有泳道

        return ParsedDocument(
            file_type="image",
            file_name=file_name,
            nodes=nodes,
            edges=edges,
            swimlanes=swimlanes,
            kcp_nodes=kcp_nodes,
            warnings=warnings,
        )

"""
维度5：流程图设计是否规范

检查项：
1. BPMN规范检查 - 开始/结束节点
2. 连线完整性 - 悬空节点、断线
3. 泳道设计 - 活动覆盖
4. 命名规范 - 节点命名
5. 网关逻辑 - 分流条件标签
6. KCP标识 - 关键控制点标记
"""
from typing import List
from app.models.schemas import (
    ParsedDocument, DimensionResult, Finding, FindingLocation,
    FlowNode, FlowEdge, Swimlane, ParseError
)
from app.utils.helpers import generate_id


class Dimension5Review:
    """流程图规范评审引擎"""

    DIM_ID = 5
    DIM_NAME = "流程图设计是否规范"

    def review(self, parsed_doc: ParsedDocument) -> DimensionResult:
        """执行维度5评审"""
        nodes = parsed_doc.nodes
        edges = parsed_doc.edges
        swimlanes = parsed_doc.swimlanes

        # 如果解析失败（有错误且无节点数据），不产出假评审
        if parsed_doc.errors and not nodes and not edges:
            error_messages = [e.message for e in parsed_doc.errors]
            error_summary = "; ".join(error_messages)
            return DimensionResult(
                dimension_id=self.DIM_ID,
                dimension_name=self.DIM_NAME,
                conclusion="无法评审",
                score=0,
                findings=[Finding(
                    finding_id=generate_id("D5_ERR"),
                    severity="严重",
                    description=f"图片解析失败，无法进行流程图规范评审。原因：{error_summary}",
                    location=FindingLocation(document_type="流程图"),
                    evidence="解析器未能从图片中提取任何流程节点和连线",
                    suggestion="请确认上传的是流程图图片，并确保使用了支持图片识别的多模态视觉模型（如 qwen-vl-max）",
                    confidence=1.0,
                )],
            )

        findings: List[Finding] = []
        total_checks = 0
        passed_checks = 0

        # 检查1: BPMN开始节点
        start_nodes = [n for n in nodes if n.node_type == 'startEvent']
        end_nodes = [n for n in nodes if n.node_type == 'endEvent']
        total_checks += 2

        if len(start_nodes) == 0:
            findings.append(Finding(
                finding_id=generate_id("D5_1"),
                severity="严重",
                description="流程图缺少开始节点，缺少流程触发点",
                location=FindingLocation(
                    document_type="流程图",
                    quote="未检测到 startEvent 类型节点",
                ),
                evidence="BPMN 2.0 规范要求流程必须包含至少一个开始事件",
                suggestion="请添加一个开始事件节点（Start Event）",
                confidence=1.0,
            ))
        elif len(start_nodes) > 1:
            findings.append(Finding(
                finding_id=generate_id("D5_1"),
                severity="一般",
                description=f"流程图包含 {len(start_nodes)} 个开始节点，可能流程分支过多",
                location=FindingLocation(
                    document_type="流程图",
                    node_id=start_nodes[1].id,
                ),
                evidence="多个开始事件表明流程可能存在未合并的入口",
                suggestion="考虑是否应合并多个入口为一个统一的开始事件",
                confidence=0.85,
            ))
        else:
            passed_checks += 1

        if len(end_nodes) == 0:
            findings.append(Finding(
                finding_id=generate_id("D5_2"),
                severity="严重",
                description="流程图缺少结束节点，流程无明确终点",
                location=FindingLocation(document_type="流程图"),
                evidence="BPMN 2.0 规范要求流程必须包含至少一个结束事件",
                suggestion="请添加结束事件节点（End Event）",
                confidence=1.0,
            ))
        else:
            passed_checks += 1

        # 检查2: 悬空节点（有入无出 或 有出无入的任务节点）
        task_nodes = [n for n in nodes if n.node_type == 'task']
        total_checks += 1

        dangling_nodes = []
        for node in task_nodes:
            has_incoming = len(node.incoming) > 0 or any(e.target == node.id for e in edges)
            has_outgoing = len(node.outgoing) > 0 or any(e.source == node.id for e in edges)
            if not has_incoming and node.node_type not in ('startEvent',):
                dangling_nodes.append((node, "缺少入边"))
            if not has_outgoing and node.node_type not in ('endEvent',):
                dangling_nodes.append((node, "缺少出边"))

        if dangling_nodes:
            for node, reason in dangling_nodes:
                findings.append(Finding(
                    finding_id=generate_id("D5_3"),
                    severity="严重" if node.node_type == 'task' else "一般",
                    description=f"节点 '{node.name or node.id}' {reason}，可能是悬空节点",
                    location=FindingLocation(
                        document_type="流程图",
                        node_id=node.id,
                    ),
                    evidence="流程节点应有明确的出入连线以保证流程连续性",
                    suggestion=f"请为节点 '{node.name or node.id}' 添加{reason.replace('缺少', '')}",
                    confidence=0.95,
                ))
        else:
            passed_checks += 1

        # 检查3: 泳道覆盖
        total_checks += 1
        if swimlanes:
            # 检查是否有活动节点不在泳道中
            all_lane_nodes = set()
            for lane in swimlanes:
                all_lane_nodes.update(lane.node_ids)

            nodes_outside_pool = [
                n for n in nodes
                if n.node_type in ('task',)
                and n.id not in all_lane_nodes
            ]
            if nodes_outside_pool:
                names = [n.name or n.id for n in nodes_outside_pool]
                findings.append(Finding(
                    finding_id=generate_id("D5_4"),
                    severity="一般",
                    description=f"有 {len(nodes_outside_pool)} 个活动节点不在泳道中: {', '.join(names[:5])}",
                    location=FindingLocation(
                        document_type="流程图",
                        node_id=nodes_outside_pool[0].id,
                    ),
                    evidence="泳道图规范要求每个活动节点明确归属于某个角色泳道",
                    suggestion="请将上述节点拖入对应角色泳道中",
                    confidence=0.9,
                ))
            else:
                passed_checks += 1
        else:
            findings.append(Finding(
                finding_id=generate_id("D5_5"),
                severity="建议",
                description="流程图未使用泳道设计，建议添加角色泳道以清晰展示角色分工",
                location=FindingLocation(document_type="流程图"),
                evidence="泳道设计是流程规范性的重要体现",
                suggestion="建议为流程图添加泳道（Lane），每个角色一个泳道",
                confidence=0.8,
            ))

        # 检查4: 节点命名规范
        total_checks += 1
        unnamed_nodes = [n for n in nodes if not n.name and n.node_type != 'sequenceFlow']
        if unnamed_nodes:
            node_types = set(n.node_type for n in unnamed_nodes)
            findings.append(Finding(
                finding_id=generate_id("D5_6"),
                severity="一般",
                description=f"有 {len(unnamed_nodes)} 个节点缺少名称（类型: {', '.join(node_types)}）",
                location=FindingLocation(
                    document_type="流程图",
                    node_id=unnamed_nodes[0].id,
                ),
                evidence="所有流程节点应有清晰可读的名称",
                suggestion="请为未命名节点添加描述性名称",
                confidence=1.0,
            ))
        else:
            passed_checks += 1

        # 检查5: 网关条件标签
        total_checks += 1
        gateway_nodes = [n for n in nodes if 'gateway' in n.node_type.lower()]
        unnamed_edges = []

        for gw in gateway_nodes:
            gw_edges = [e for e in edges if e.source == gw.id]
            for e in gw_edges:
                if not e.name:
                    unnamed_edges.append((gw, e))

        if unnamed_edges:
            for gw, edge in unnamed_edges:
                findings.append(Finding(
                    finding_id=generate_id("D5_7"),
                    severity="一般",
                    description=f"网关 '{gw.name or gw.id}' 有出边缺少条件标签",
                    location=FindingLocation(
                        document_type="流程图",
                        node_id=gw.id,
                        quote=f"连线: {edge.source} -> {edge.target}"
                    ),
                    evidence="网关的分支出边应标注条件以明确分流逻辑",
                    suggestion="请为网关的出边添加条件描述（如 批准/驳回 ）",
                    confidence=0.95,
                ))
        else:
            passed_checks += 1

        # 检查6: KCP 标识
        total_checks += 1
        kcp_ids = parsed_doc.kcp_nodes
        if not kcp_ids:
            findings.append(Finding(
                finding_id=generate_id("D5_8"),
                severity="建议",
                description="流程图中未标识任何关键控制点（KCP），请确认是否存在需要标识的控制活动",
                location=FindingLocation(document_type="流程图"),
                evidence="关键控制点应在流程图中显式标识",
                suggestion="请在关键控制活动中添加 KCP 标记",
                confidence=0.75,
            ))
        else:
            passed_checks += 1

        # 计算分数
        score = int((passed_checks / total_checks) * 100) if total_checks > 0 else 100
        conclusion = self._get_conclusion(score, findings)

        return DimensionResult(
            dimension_id=self.DIM_ID,
            dimension_name=self.DIM_NAME,
            conclusion=conclusion,
            score=score,
            findings=findings,
        )

    def _get_conclusion(self, score: int, findings: List[Finding]) -> str:
        """根据分数和问题确定结论"""
        has_critical = any(f.severity == "严重" for f in findings)
        if score < 50 or has_critical:
            return "不通过"
        elif score < 75:
            return "需关注"
        else:
            return "通过"

"""
BPMN 2.0 XML 流程图解析器

解析 BPMN 2.0 XML 文件，提取：
- 节点（开始、结束、任务、网关等）
- 连线（序列流）
- 泳道（Lane）
- KCP 标记节点
- 节点名称和描述
"""
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Set
from app.models.schemas import (
    ParsedDocument, FlowNode, FlowEdge, Swimlane,
    ParseError, Section, Role, Activity, Risk, KPI, FormField
)
from app.utils.helpers import normalize_name


class BpmnParser:
    """BPMN 2.0 XML 解析器"""

    # BPMN 命名空间
    BPMN_NS = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
    BPMNDI_NS = 'http://www.omg.org/spec/BPMN/20100524/DI'

    # 节点类型映射
    NODE_TYPE_MAP = {
        'startEvent': 'startEvent',
        'endEvent': 'endEvent',
        'task': 'task',
        'userTask': 'task',
        'serviceTask': 'task',
        'scriptTask': 'task',
        'sendTask': 'task',
        'receiveTask': 'task',
        'manualTask': 'task',
        'businessRuleTask': 'task',
        'exclusiveGateway': 'exclusiveGateway',
        'inclusiveGateway': 'inclusiveGateway',
        'parallelGateway': 'parallelGateway',
        'complexGateway': 'exclusiveGateway',
        'eventBasedGateway': 'exclusiveGateway',
        'intermediateCatchEvent': 'intermediateEvent',
        'intermediateThrowEvent': 'intermediateEvent',
        'boundaryEvent': 'intermediateEvent',
        'subProcess': 'subProcess',
        'callActivity': 'task',
    }

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.warnings: List[str] = []
        self.errors: List[ParseError] = []
        self.ns = {'bpmn': self.BPMN_NS}

    def parse(self) -> ParsedDocument:
        """解析 BPMN 文件"""
        try:
            # 尝试自动检测命名空间
            tree = ET.parse(self.file_path)
            root = tree.getroot()

            # 检测 BPMN 命名空间
            tag = root.tag.lower()
            if 'bpmn' not in tag and 'definitions' not in tag:
                self.errors.append(ParseError(
                    type="structure_error",
                    message="非标准 BPMN 2.0 文件",
                    suggestion="请确认文件是否为标准 BPMN 2.0 格式"
                ))
                return self._empty_result()

            # 提取命名空间
            ns_match = re.match(r'\{(.+?)\}', root.tag)
            if ns_match:
                self.ns = {'bpmn': ns_match.group(1)}

            # 检查是否有 process 元素
            processes = root.findall('.//bpmn:process', self.ns)
            if not processes:
                self.errors.append(ParseError(
                    type="structure_error",
                    message="BPMN 文件解析失败，未找到 process 元素",
                    suggestion="请检查是否为标准 BPMN 2.0 格式"
                ))
                return self._empty_result()

            # 解析各元素
            nodes = self._parse_nodes(root)
            edges = self._parse_edges(root)
            swimlanes = self._parse_swimlanes(root, nodes)
            kcp_nodes = self._identify_kcp_nodes(nodes)

            # 更新节点的泳道归属
            self._assign_lanes_to_nodes(nodes, swimlanes)

            # 后验证
            self._validate_diagram(nodes, edges, swimlanes)

        except ET.ParseError as e:
            self.errors.append(ParseError(
                type="structure_error",
                message=f"XML 解析错误: {str(e)}",
                suggestion="请检查文件是否为有效的 BPMN 2.0 XML"
            ))
            return self._empty_result()
        except Exception as e:
            self.errors.append(ParseError(
                type="structure_error",
                message=f"BPMN 解析异常: {str(e)}",
            ))
            return self._empty_result()

        return ParsedDocument(
            file_type="bpmn",
            file_name=self.file_path.split('/')[-1],
            nodes=nodes,
            edges=edges,
            swimlanes=swimlanes,
            kcp_nodes=kcp_nodes,
            full_text=self._generate_text(nodes, edges, swimlanes),
            warnings=self.warnings,
            errors=self.errors,
        )

    def _parse_nodes(self, root: ET.Element) -> List[FlowNode]:
        """解析所有流程节点"""
        nodes: List[FlowNode] = []
        seen_ids: Set[str] = set()

        for tag_name, node_type in self.NODE_TYPE_MAP.items():
            for elem in root.findall(f'.//bpmn:{tag_name}', self.ns):
                node_id = elem.get('id', '')
                if not node_id or node_id in seen_ids:
                    continue
                seen_ids.add(node_id)

                name = elem.get('name', '') or ''
                documentation = ''

                # 获取文档描述
                doc_elem = elem.find('bpmn:documentation', self.ns)
                if doc_elem is not None and doc_elem.text:
                    documentation = doc_elem.text.strip()

                # 获取出入边
                outgoing_ids: List[str] = []
                incoming_ids: List[str] = []

                for out_elem in elem.findall('bpmn:outgoing', self.ns):
                    flow_ref = out_elem.text or ''
                    if flow_ref:
                        outgoing_ids.append(flow_ref)

                # incoming 可能是通过序列流指向此节点
                # 我们在解析边时再处理

                is_kcp = self._check_kcp(name, elem)

                nodes.append(FlowNode(
                    id=node_id,
                    name=name,
                    node_type=node_type,
                    outgoing=outgoing_ids,
                    incoming=[],  # 后续填充
                    is_kcp=is_kcp,
                    documentation=documentation,
                ))

        return nodes

    def _parse_edges(self, root: ET.Element) -> List[FlowEdge]:
        """解析序列流（连线）"""
        edges: List[FlowEdge] = []
        seen_ids: Set[str] = set()

        for elem in root.findall('.//bpmn:sequenceFlow', self.ns):
            edge_id = elem.get('id', '')
            if not edge_id or edge_id in seen_ids:
                continue
            seen_ids.add(edge_id)

            source_ref = elem.get('sourceRef', '')
            target_ref = elem.get('targetRef', '')
            name = elem.get('name', '') or ''

            edges.append(FlowEdge(
                id=edge_id,
                source=source_ref,
                target=target_ref,
                name=name if name else None,
            ))

        return edges

    def _parse_swimlanes(self, root: ET.Element, nodes: List[FlowNode]) -> List[Swimlane]:
        """解析泳道"""
        swimlanes: List[Swimlane] = []
        seen_ids: Set[str] = set()

        # 通过 flowNodeRef 收集泳道包含的节点
        lane_node_map: Dict[str, List[str]] = {}

        for elem in root.findall('.//bpmn:lane', self.ns):
            lane_id = elem.get('id', '')
            lane_name = elem.get('name', '流程角色')

            if not lane_id or lane_id in seen_ids:
                continue
            seen_ids.add(lane_id)

            node_ids: List[str] = []
            for flow_ref in elem.findall('bpmn:flowNodeRef', self.ns):
                ref_text = flow_ref.text or ''
                if ref_text:
                    node_ids.append(ref_text)

            swimlanes.append(Swimlane(
                id=lane_id,
                name=lane_name,
                node_ids=node_ids,
            ))

        return swimlanes

    def _identify_kcp_nodes(self, nodes: List[FlowNode]) -> List[str]:
        """识别 KCP 标记节点"""
        kcp_ids: List[str] = []
        for node in nodes:
            if node.is_kcp:
                kcp_ids.append(node.id)
        return kcp_ids

    def _check_kcp(self, name: str, elem: ET.Element) -> bool:
        """检查节点是否有 KCP 标记"""
        # 1. 名称检查
        name_lower = name.lower()
        kcp_keywords = ['kcp', '关键控制点', '控制点']
        if any(kw in name_lower for kw in kcp_keywords):
            return True

        # 2. 扩展属性检查
        for ext_elem in elem.findall('.//bpmn:extensionElements', self.ns):
            ext_text = ET.tostring(ext_elem, encoding='unicode').lower()
            if 'kcp' in ext_text:
                return True

        return False

    def _assign_lanes_to_nodes(self, nodes: List[FlowNode], swimlanes: List[Swimlane]):
        """将泳道归属分配到节点"""
        # 构建 节点ID -> 泳道ID 映射
        node_to_lane: Dict[str, str] = {}
        for lane in swimlanes:
            for node_id in lane.node_ids:
                node_to_lane[node_id] = lane.id

        for node in nodes:
            if node.id in node_to_lane:
                node.lane_id = node_to_lane[node.id]

        # 填充节点的 incoming 列表
        node_map = {n.id: n for n in nodes}
        for edge in self._edges_cache if hasattr(self, '_edges_cache') else []:
            pass

    def _validate_diagram(self, nodes: List[FlowNode], edges: List[FlowEdge], swimlanes: List[Swimlane]):
        """图表规则验证"""
        node_map = {n.id: n for n in nodes}

        # 填充 incoming
        for edge in edges:
            if edge.target in node_map:
                node_map[edge.target].incoming.append(edge.id)

        # 1. 开始节点检查
        start_nodes = [n for n in nodes if n.node_type == 'startEvent']
        if len(start_nodes) == 0:
            self.errors.append(ParseError(
                type="structure_error",
                message="流程图缺少开始节点",
                suggestion="请添加一个开始事件节点"
            ))
        elif len(start_nodes) > 1:
            self.warnings.append("流程图包含多个开始节点")

        # 2. 结束节点检查
        end_nodes = [n for n in nodes if n.node_type == 'endEvent']
        if len(end_nodes) == 0:
            self.errors.append(ParseError(
                type="structure_error",
                message="流程图缺少结束节点",
                suggestion="请添加至少一个结束事件节点"
            ))

        # 3. 悬空节点检查（任务节点必须有入有出）
        for node in nodes:
            if node.node_type == 'task':
                if not node.incoming and not any(
                    e.target == node.id for e in edges
                ):
                    self.warnings.append(
                        f"节点 '{node.name or node.id}' 无入边，可能是悬空节点"
                    )
                if not node.outgoing and not any(
                    e.source == node.id for e in edges
                ):
                    self.warnings.append(
                        f"节点 '{node.name or node.id}' 无出边，可能是悬空节点"
                    )

        # 4. 网关条件标签检查
        gateway_nodes = [n for n in nodes if 'gateway' in n.node_type.lower()]
        for gw in gateway_nodes:
            gw_edges = [e for e in edges if e.source == gw.id]
            unnamed = [e for e in gw_edges if not e.name]
            if unnamed:
                self.warnings.append(
                    f"网关 '{gw.name or gw.id}' 的 {len(unnamed)} 条出边缺少条件标签"
                )

        # 5. 泳道外节点检查
        if swimlanes:
            all_lane_nodes: Set[str] = set()
            for lane in swimlanes:
                all_lane_nodes.update(lane.node_ids)

            for node in nodes:
                if node.node_type in ('task', 'startEvent', 'endEvent', 'intermediateEvent'):
                    if node.id not in all_lane_nodes:
                        self.warnings.append(
                            f"节点 '{node.name or node.id}' 不在任何泳道中"
                        )

    def _generate_text(self, nodes: List[FlowNode], edges: List[FlowEdge], swimlanes: List[Swimlane]) -> str:
        """生成可读文本用于 AI 理解"""
        lines = ["# 流程图结构"]

        if swimlanes:
            lines.append("\n## 泳道（角色）")
            for lane in swimlanes:
                lines.append(f"- {lane.name} ({len(lane.node_ids)} 个节点)")

        lines.append("\n## 节点列表")
        for node in nodes:
            kcp_mark = " [KCP]" if node.is_kcp else ""
            lane_name = ""
            if node.lane_id:
                lane = next((l for l in swimlanes if l.id == node.lane_id), None)
                if lane:
                    lane_name = f" @{lane.name}"
            lines.append(f"- [{node.node_type}] {node.name or '(未命名)'}{lane_name}{kcp_mark}")

        lines.append("\n## 连线")
        for edge in edges:
            src = next((n.name for n in nodes if n.id == edge.source), edge.source)
            tgt = next((n.name for n in nodes if n.id == edge.target), edge.target)
            cond = f" [{edge.name}]" if edge.name else ""
            lines.append(f"- {src} -> {tgt}{cond}")

        return '\n'.join(lines)

    def _empty_result(self) -> ParsedDocument:
        return ParsedDocument(
            file_type="bpmn",
            file_name=self.file_path.split('/')[-1],
            full_text="",
            warnings=self.warnings,
            errors=self.errors,
        )

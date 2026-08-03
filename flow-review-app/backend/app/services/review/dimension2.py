"""
维度2：流程活动和角色职责是否匹配

检查项：
1. 说明书中的角色在流程图中是否有对应泳道/节点
2. 流程图中泳道角色在说明书中是否定义
3. 活动是否分配了执行角色
4. 跨泳道角色的合理性
"""
from typing import List, Set, Dict, Optional
from app.models.schemas import (
    ParsedDocument, DimensionResult, Finding, FindingLocation,
    Role, Activity, Swimlane, FlowNode
)
from app.utils.helpers import generate_id, fuzzy_match, normalize_name


class Dimension2Review:
    """角色职责匹配评审引擎"""

    DIM_ID = 2
    DIM_NAME = "流程活动和角色职责是否匹配"

    def review(self, manual_doc: ParsedDocument, diagram_doc: ParsedDocument) -> DimensionResult:
        """执行维度2评审"""
        roles = manual_doc.role_table
        activities = manual_doc.activity_table
        swimlanes = diagram_doc.swimlanes
        nodes = diagram_doc.nodes
        findings: List[Finding] = []
        total_checks = 0
        passed_checks = 0

        # 检查1: 说明书角色 vs 流程图泳道匹配
        total_checks += 1
        role_names = [normalize_name(r.name) for r in roles]
        swimlane_names = [normalize_name(s.name) for s in swimlanes]

        missing_in_diagram: List[Role] = []
        matched_roles = set()

        for role in roles:
            role_norm = normalize_name(role.name)
            found = False
            for sw in swimlanes:
                sw_norm = normalize_name(sw.name)
                if role_norm == sw_norm or fuzzy_match(role_norm, sw_norm) > 0.7:
                    found = True
                    matched_roles.add(role.name)
                    break
            if not found and swimlanes:
                missing_in_diagram.append(role)

        if missing_in_diagram:
            for role in missing_in_diagram:
                findings.append(Finding(
                    finding_id=generate_id("D2_1"),
                    severity="一般",
                    description=f"说明书定义的角色 '{role.name}' 在流程图中未找到对应的泳道",
                    location=FindingLocation(
                        document_type="说明书",
                        section="角色与职责",
                        quote=f"角色: {role.name}",
                    ),
                    evidence="角色应在流程泳道图中体现以展示职责分工",
                    suggestion=f"请在流程图中为 '{role.name}' 添加对应泳道",
                    confidence=0.85,
                ))
        elif swimlanes:
            passed_checks += 1

        # 检查2: 流程图泳道 vs 说明书角色匹配
        total_checks += 1
        extra_in_diagram: List[Swimlane] = []
        for sw in swimlanes:
            sw_norm = normalize_name(sw.name)
            found = False
            for role in roles:
                role_norm = normalize_name(role.name)
                if sw_norm == role_norm or fuzzy_match(sw_norm, role_norm) > 0.7:
                    found = True
                    break
            if not found:
                extra_in_diagram.append(sw)

        if extra_in_diagram:
            for sw in extra_in_diagram:
                findings.append(Finding(
                    finding_id=generate_id("D2_2"),
                    severity="建议",
                    description=f"流程图泳道 '{sw.name}' 在说明书角色表中未定义",
                    location=FindingLocation(
                        document_type="流程图",
                        node_id=sw.id,
                    ),
                    evidence="所有泳道角色应在说明书的角色表中明确定义",
                    suggestion=f"请在说明书中添加角色 '{sw.name}' 的定义",
                    confidence=0.8,
                ))
        else:
            passed_checks += 1

        # 检查3: 活动是否分配了执行角色
        total_checks += 1
        unassigned_activities = [a for a in activities if not a.role]
        if unassigned_activities:
            for act in unassigned_activities[:5]:  # 限制数量
                findings.append(Finding(
                    finding_id=generate_id("D2_3"),
                    severity="一般",
                    description=f"活动 '{act.name}' 未指定执行角色",
                    location=FindingLocation(
                        document_type="说明书",
                        quote=f"活动: {act.name}",
                    ),
                    evidence="每个流程活动应明确指定执行角色",
                    suggestion=f"请为活动 '{act.name}' 标注执行角色",
                    confidence=0.9,
                ))
        elif activities:
            passed_checks += 1

        # 检查4: 活动角色与泳道节点归属一致性
        total_checks += 1
        if activities and swimlanes and nodes:
            mismatches = self._check_activity_lane_consistency(
                activities, swimlanes, nodes, roles
            )
            if mismatches:
                for activity_name, assigned_role, actual_lane in mismatches[:3]:
                    findings.append(Finding(
                        finding_id=generate_id("D2_4"),
                        severity="一般",
                        description=(
                            f"活动 '{activity_name}' 指定角色为 '{assigned_role}'，"
                            f"但在流程图中该活动位于泳道 '{actual_lane}'"
                        ),
                        location=FindingLocation(
                            document_type="说明书",
                            section="流程活动描述",
                            quote=f"活动: {activity_name} / 角色: {assigned_role}",
                        ),
                        evidence="同一活动的角色归属在说明书和流程图中应保持一致",
                        suggestion="请核实活动角色归属的准确性",
                        confidence=0.7,
                    ))
            else:
                passed_checks += 1
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

    def _check_activity_lane_consistency(
        self,
        activities: List[Activity],
        swimlanes: List[Swimlane],
        nodes: List[FlowNode],
        roles: List[Role],
    ) -> List[tuple]:
        """检查活动角色与泳道节点归属的一致性"""
        mismatches = []

        for activity in activities:
            if not activity.role:
                continue

            assigned_role_norm = normalize_name(activity.role)
            activity_name_norm = normalize_name(activity.name)

            # 在流程图中找名称匹配的节点
            for node in nodes:
                if node.node_type != 'task':
                    continue
                node_name_norm = normalize_name(node.name)
                if fuzzy_match(activity_name_norm, node_name_norm) > 0.6:
                    # 找到匹配节点，检查泳道归属
                    if node.lane_id:
                        lane = next(
                            (l for l in swimlanes if l.id == node.lane_id),
                            None
                        )
                        if lane:
                            lane_norm = normalize_name(lane.name)
                            if fuzzy_match(assigned_role_norm, lane_norm) < 0.6:
                                mismatches.append((
                                    activity.name,
                                    activity.role,
                                    lane.name,
                                ))
                    break

        return mismatches

    def _get_conclusion(self, score: int, findings: List[Finding]) -> str:
        has_critical = any(f.severity == "严重" for f in findings)
        if score < 50 or has_critical:
            return "不通过"
        elif score < 75:
            return "需关注"
        else:
            return "通过"

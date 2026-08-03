"""
Markdown 说明书解析器

解析 Markdown 格式的流程说明书，提取：
- 章节结构（H1/H2/H3标题和内容）
- 角色清单表格
- 活动清单
- 风险清单
- KPI指标
- 附件清单
"""
import re
from typing import List, Dict, Optional, Tuple
from app.models.schemas import (
    ParsedDocument, Section, Role, Activity, Risk, KPI,
    ParseError, FormField, FlowNode, FlowEdge, Swimlane
)
from app.utils.helpers import normalize_name


class MarkdownParser:
    """Markdown 说明书解析器"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.warnings: List[str] = []
        self.errors: List[ParseError] = []

    def parse(self) -> ParsedDocument:
        """解析 Markdown 文件为统一结构"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(self.file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                self.warnings.append("文件编码非 UTF-8，已尝试 GBK 解码")
            except Exception as e:
                self.errors.append(ParseError(
                    type="encoding_error",
                    message=f"文件编码错误: {str(e)}",
                    suggestion="请将文件保存为 UTF-8 编码"
                ))
                return self._empty_result()

        lines = content.split('\n')
        file_name = self.file_path.split('/')[-1]

        # 1. 解析章节
        sections = self._parse_sections(lines)

        # 2. 验证章节数量
        h2_count = sum(1 for s in sections if s.level == 2)
        if h2_count < 3:
            self.warnings.append(
                f"说明书章节结构不完整（仅有 {h2_count} 个 H2 标题），"
                "请检查是否使用了标准标题样式"
            )

        # 3. 解析角色表格
        role_table = self._parse_role_table(sections)

        # 4. 解析活动清单
        activity_table = self._parse_activities(sections)

        # 5. 解析风险表格
        risk_table = self._parse_risk_table(sections)

        # 6. 解析 KPI 表格
        kpi_table = self._parse_kpi_table(sections)

        return ParsedDocument(
            file_type="markdown",
            file_name=file_name,
            sections=sections,
            role_table=role_table,
            activity_table=activity_table,
            risk_table=risk_table,
            kpi_table=kpi_table,
            full_text=content,
            nodes=[],
            edges=[],
            swimlanes=[],
            kcp_nodes=[],
            form_fields=[],
            warnings=self.warnings,
            errors=self.errors,
        )

    def _parse_sections(self, lines: List[str]) -> List[Section]:
        """解析 Markdown 标题结构"""
        sections: List[Section] = []
        current_section: Optional[Dict] = None
        current_lines: List[str] = []

        for i, line in enumerate(lines):
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                # 保存前一个section
                if current_section:
                    current_section['content'] = '\n'.join(current_lines).strip()
                    sections.append(Section(**current_section))

                level = len(match.group(1))
                title = match.group(2).strip()
                anchor = self._make_anchor(title)

                current_section = {
                    'title': title,
                    'level': level,
                    'anchor': anchor,
                    'content': '',
                }
                current_lines = []
            elif current_section:
                current_lines.append(line)

        # 保存最后一个section
        if current_section:
            current_section['content'] = '\n'.join(current_lines).strip()
            sections.append(Section(**current_section))

        return sections

    def _make_anchor(self, title: str) -> str:
        """生成锚点"""
        anchor = re.sub(r'[^\w\u4e00-\u9fff\s]', '', title.lower())
        anchor = re.sub(r'\s+', '-', anchor.strip())
        return anchor

    def _parse_role_table(self, sections: List[Section]) -> List[Role]:
        """从名称中包含"角色"的章节提取角色表格"""
        role_sections = [
            s for s in sections
            if any(kw in s.title.lower() for kw in ['角色', '职责', 'role'])
        ]

        roles: List[Role] = []
        for section in role_sections:
            rows = self._extract_table_rows(section.content)
            for row in rows:
                if len(row) >= 1:
                    name = row[0].strip()
                    if name and not any(kw in name.lower() for kw in ['角色', 'role', '名称', 'name', '---']):
                        duty = row[1].strip() if len(row) > 1 else None
                        roles.append(Role(name=name, duty=duty))

        return roles

    def _find_parent_activity_section(self, sections: List[Section]) -> Optional[Section]:
        """查找包含活动关键词的父章节"""
        for s in sections:
            if s.level <= 2 and any(
                kw in s.title.lower() for kw in ['活动', '流程步骤', 'activity']
            ):
                return s
        return None

    def _get_child_sections(self, sections: List[Section], parent_title: str) -> List[Section]:
        """获取指定父章节下的所有子章节"""
        children = []
        in_parent = False
        for s in sections:
            if s.title == parent_title:
                in_parent = True
                continue
            if in_parent:
                if s.level <= 2:  # 遇到同级或更高级标题，停止
                    break
                if s.level >= 3:
                    children.append(s)
        return children

    def _parse_activities(self, sections: List[Section]) -> List[Activity]:
        """从活动描述章节提取活动"""
        activities: List[Activity] = []

        # 查找活动相关章节
        activity_sections = [
            s for s in sections
            if any(kw in s.title.lower() for kw in ['活动', '流程步骤', 'activity'])
        ]

        for section in activity_sections:
            # 子章节可能是具体活动
            if section.level >= 3:
                role = self._extract_field(section.content, r'执行角色[：:]\s*(.+)')
                inputs = self._extract_field(section.content, r'输入[：:]\s*(.+)')
                outputs = self._extract_field(section.content, r'输出[：:]\s*(.+)')

                activities.append(Activity(
                    name=section.title,
                    role=role,
                    inputs=inputs,
                    outputs=outputs,
                    description=section.content[:200] if section.content else None,
                ))

            # 找到父章节的子章节
            if section.level == 2:
                children = self._get_child_sections(sections, section.title)
                for child in children:
                    role = self._extract_field(child.content, r'\*?\*?执行角色\*?\*?[：:]\s*(.+)')
                    inputs = self._extract_field(child.content, r'\*?\*?输入\*?\*?[：:]\s*(.+)')
                    outputs = self._extract_field(child.content, r'\*?\*?输出\*?\*?[：:]\s*(.+)')

                    activities.append(Activity(
                        name=child.title,
                        role=role,
                        inputs=inputs,
                        outputs=outputs,
                        description=child.content[:200] if child.content else None,
                    ))

            # 也尝试从表格提取
            rows = self._extract_table_rows(section.content)
            for row in rows:
                if len(row) >= 1:
                    name = row[0].strip()
                    if name and not any(kw in name.lower() for kw in ['活动', 'activity', '名称', '---']):
                        role = row[1].strip() if len(row) > 1 else None
                        desc = row[-1].strip() if len(row) > 2 and len(row[-1]) > 5 else None
                        activities.append(Activity(
                            name=name,
                            role=role,
                            description=desc,
                        ))

        return activities

    def _parse_risk_table(self, sections: List[Section]) -> List[Risk]:
        """从风险章节提取风险清单"""
        risk_sections = [
            s for s in sections
            if any(kw in s.title.lower() for kw in ['风险', 'risk', '控制'])
        ]

        risks: List[Risk] = []
        for section in risk_sections:
            rows = self._extract_table_rows(section.content)
            for row in rows:
                if len(row) >= 1:
                    name = row[0].strip()
                    if name and not any(kw in name.lower() for kw in ['风险', 'risk', '名称', '---']):
                        control = row[1].strip() if len(row) > 1 else None
                        is_kcp = False
                        if len(row) > 2:
                            kcp_text = row[2].strip().lower()
                            is_kcp = kcp_text in ['是', 'yes', 'true', 'kcp', '控制点']
                        risks.append(Risk(
                            name=name,
                            control_measure=control,
                            is_kcp=is_kcp,
                        ))

        return risks

    def _parse_kpi_table(self, sections: List[Section]) -> List[KPI]:
        """从指标章节提取KPI"""
        kpi_sections = [
            s for s in sections
            if any(kw in s.title.lower() for kw in ['指标', 'kpi', '绩效', '衡量'])
        ]

        kpis: List[KPI] = []
        for section in kpi_sections:
            rows = self._extract_table_rows(section.content)
            for row in rows:
                if len(row) >= 1:
                    name = row[0].strip()
                    if name and not any(kw in name.lower() for kw in ['指标', 'kpi', '名称', '---']):
                        target = row[1].strip() if len(row) > 1 else None
                        calc = row[2].strip() if len(row) > 2 else None
                        kpis.append(KPI(
                            name=name,
                            target_value=target,
                            calculation=calc,
                        ))

        return kpis

    def _extract_table_rows(self, content: str) -> List[List[str]]:
        """从 Markdown 表格中提取行数据"""
        rows: List[List[str]] = []
        for line in content.split('\n'):
            line = line.strip()
            # 跳过非表格行（分隔线 |---|---|）
            if not line.startswith('|'):
                continue
            if re.match(r'^[\|\s\-:]+$', line):
                continue

            cells = [cell.strip() for cell in line.split('|')]
            # 去掉首尾空元素
            cells = [c for c in cells if c]
            if cells:
                rows.append(cells)

        return rows

    def _extract_field(self, content: str, pattern: str) -> Optional[str]:
        """用正则提取字段值"""
        match = re.search(pattern, content, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _empty_result(self) -> ParsedDocument:
        """返回空结果"""
        return ParsedDocument(
            file_type="markdown",
            file_name=self.file_path.split('/')[-1],
            full_text="",
            warnings=self.warnings,
            errors=self.errors,
        )

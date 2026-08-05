"""
评审标准解析器 —— 从所有已录入的标准文档中提取、整合为统一的分类分级结构
"""
import os
import re
from typing import Optional


def parse_standards(knowledge_dir: str) -> dict:
    """
    读取 knowledge_docs 目录下所有 Markdown 文件，
    解析为统一的「分类 → 章节 → 规则」层级结构。
    """
    categories: list[dict] = []
    source_count = 0

    if not os.path.isdir(knowledge_dir):
        return _empty_result()

    for filename in sorted(os.listdir(knowledge_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(knowledge_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        parsed = _parse_markdown(content)
        if parsed["categories"]:
            categories.extend(parsed["categories"])
            source_count += 1

    if not categories:
        return _empty_result()

    # 合并同类 Category
    merged = _merge_categories(categories)
    # 为每一条规则编序号
    merged = _reindex(merged)

    return {
        "title": "评审标准",
        "source_count": source_count,
        "categories": merged,
    }


def _empty_result() -> dict:
    return {"title": "评审标准", "source_count": 0, "categories": []}


# ---------- Markdown 解析 ----------

def _parse_markdown(text: str) -> dict:
    """将 Markdown 文本解析为分类结构"""
    categories: list[dict] = []
    current_category: Optional[dict] = None
    current_section: Optional[dict] = None
    pending_lines: list[str] = []

    def flush_section():
        nonlocal current_section, pending_lines
        if current_section and current_category is not None:
            rules = _extract_rules(pending_lines)
            if rules:
                current_section["rules"] = rules
                current_category.setdefault("sections", []).append(current_section)
        current_section = None
        pending_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # H2 → Category
        if stripped.startswith("## ") and not stripped.startswith("### "):
            flush_section()
            if current_category is not None:
                categories.append(current_category)
            current_category = {"title": stripped[3:].strip(), "sections": []}
            continue

        # H3 → Section
        if stripped.startswith("### "):
            flush_section()
            title = stripped[4:].strip()
            current_section = {"title": title}
            continue

        # 所有非标题行作为待提取的规则内容
        if current_category is not None:
            pending_lines.append(stripped)

    flush_section()
    if current_category is not None:
        categories.append(current_category)

    # 如果没有解析到任何分类（文档没有 ## / ### 标题），
    # 把整个文档当作一个「未分类规则」兜底解析
    if not any(c.get("sections") for c in categories):
        fallback = _parse_fallback(text)
        if fallback:
            categories = [fallback]

    return {"categories": [c for c in categories if c.get("sections")]}


def _extract_rules(lines: list[str]) -> list[dict]:
    """从一组文本行中提取规则列表"""
    rules: list[dict] = []
    for line in lines:
        # 跳过空行
        if not line:
            continue
        # 移除行首编号 "1. " / "1、" / "（1）" 等
        cleaned = re.sub(r'^[\s]*[（(]?\d+[)）\.\、]\s*', '', line).strip()
        if not cleaned:
            cleaned = line.strip()
        # 过滤太短的无意义行
        if len(cleaned) < 3:
            continue
        # 避免完全重复
        if any(r["content"] == cleaned for r in rules):
            continue
        rules.append({"content": cleaned})
    return rules


def _parse_fallback(text: str) -> Optional[dict]:
    """兜底解析：文档没有 ## / ### 标题时，把所有编号列表/段落当作规则"""
    title = "未分类规则"
    lines: list[str] = []

    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        # 用 H1 作为分类标题
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            continue
        lines.append(stripped)

    rules = _extract_rules(lines)
    if not rules:
        return None

    return {
        "title": title,
        "sections": [{"title": "规则条目", "rules": rules}],
    }


# ---------- 合并 & 去重 ----------

def _merge_categories(categories: list[dict]) -> list[dict]:
    """合并同名 Category，合并同类 Section，去重规则"""
    cat_map: dict[str, dict] = {}

    for cat in categories:
        key = cat["title"]
        if key not in cat_map:
            cat_map[key] = {"title": key, "sections": []}

        for sec in cat.get("sections", []):
            existing_sec = _find_section(cat_map[key]["sections"], sec["title"])
            if existing_sec:
                # 合并规则，去重
                existing_rules = {r["content"] for r in existing_sec.get("rules", [])}
                for rule in sec.get("rules", []):
                    if rule["content"] not in existing_rules:
                        existing_sec["rules"].append(rule)
                        existing_rules.add(rule["content"])
            else:
                cat_map[key]["sections"].append(sec)

    return list(cat_map.values())


def _find_section(sections: list[dict], title: str) -> Optional[dict]:
    for sec in sections:
        if sec["title"] == title:
            return sec
    return None


# ---------- 重新编号 ----------

def _reindex(categories: list[dict]) -> list[dict]:
    """重新为所有规则编号，形如 1.1, 1.2, 2.1..."""
    for ci, cat in enumerate(categories, 1):
        for si, sec in enumerate(cat.get("sections", []), 1):
            for ri, rule in enumerate(sec.get("rules", []), 1):
                rule["index"] = f"{ci}.{si}.{ri}"
    return categories

"""
简易知识库检索服务

MVP阶段使用关键词匹配+规则检索，后续升级为 ChromaDB 向量检索
"""
import os
import re
import json
from typing import List, Dict, Optional, Tuple
from app.core.database import get_connection


class KnowledgeSearch:
    """知识库关键词检索器"""

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._index: Dict[str, List[str]] = {}  # keyword -> [doc_ids]
        self._loaded = False

    def _ensure_loaded(self):
        """加载知识库文档到内存缓存"""
        if self._loaded:
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, file_path FROM knowledge_docs")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            doc_id = row["id"]
            file_path = row["file_path"]
            if os.path.exists(file_path):
                content = ""
                ext = os.path.splitext(file_path)[1].lower()
                try:
                    if ext in ('.md', '.txt', '.json'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    self._cache[doc_id] = content
                except Exception:
                    pass

        self._loaded = True

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        关键词搜索

        Args:
            query: 搜索查询
            top_k: 返回前k个结果

        Returns:
            [{doc_id, title, content_snippet, score, metadata}]
        """
        self._ensure_loaded()

        if not self._cache:
            return []

        keywords = self._extract_keywords(query)
        results = []

        conn = get_connection()
        cursor = conn.cursor()

        for doc_id, content in self._cache.items():
            score = self._calculate_keyword_score(keywords, content)

            if score > 0:
                cursor.execute(
                    "SELECT title, doc_type FROM knowledge_docs WHERE id = ?",
                    (doc_id,)
                )
                row = cursor.fetchone()
                if row:
                    snippet = self._get_snippet(content, keywords, 200)
                    results.append({
                        "doc_id": doc_id,
                        "title": row["title"],
                        "doc_type": row["doc_type"],
                        "content_snippet": snippet,
                        "score": score,
                    })

        conn.close()

        # 按分数降序排列
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_context_for_review(self, dimension: str, query_texts: List[str]) -> str:
        """
        获取评审所需的上下文知识

        Args:
            dimension: 评审维度
            query_texts: 待评审的文本片段

        Returns:
            拼接的上下文文本
        """
        all_keywords = set()
        for text in query_texts:
            all_keywords.update(self._extract_keywords(text))

        # 维度关键词映射
        dimension_keywords = {
            "维度1": ["方案设计", "业务需求", "设计意图"],
            "维度2": ["角色", "职责", "权限"],
            "维度3": ["风险", "控制", "KCP"],
            "维度4": ["业务场景", "场景"],
            "维度5": ["流程图", "BPMN", "规范", "泳道"],
            "维度6": ["指标", "KPI", "绩效"],
            "维度7": ["表单", "模板", "字段"],
            "维度8": ["附件", "标准"],
        }

        extra_keywords = dimension_keywords.get(dimension, [])
        all_keywords.update(extra_keywords)

        query = " ".join(all_keywords)
        matches = self.search(query, top_k=3)

        if not matches:
            return ""

        contexts = []
        for m in matches:
            self._ensure_loaded()
            full_content = self._cache.get(m["doc_id"], "")
            if full_content:
                contexts.append(f"## 参考文档: {m['title']}\n{full_content[:800]}")

        return "\n\n".join(contexts)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 去除 Markdown 标记和特殊字符
        clean = re.sub(r'[#*_`\[\]()]+', ' ', text.lower())
        clean = re.sub(r'[^\w\u4e00-\u9fff\s]', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()

        words = clean.split()
        # 过滤短词和常见停用词
        stop_words = {
            '是', '的', '了', '在', '和', '与', '或', '及', '等',
            'the', 'a', 'an', 'is', 'are', 'of', 'to', 'in', 'for',
            '为', '使用', '可以', '通过', '进行', '需要', '一个',
        }
        keywords = []
        for w in words:
            if len(w) >= 2 and w not in stop_words:
                keywords.append(w)

        return list(set(keywords))[:20]  # 限制关键词数量

    def _calculate_keyword_score(self, keywords: List[str], content: str) -> float:
        """计算关键词匹配分数"""
        if not keywords:
            return 0.0

        content_lower = content.lower()
        total_weight = 0
        for kw in keywords:
            # 精确匹配权重更高
            if kw in content_lower:
                total_weight += 1.0
            else:
                # 部分匹配
                for i in range(len(kw), 1, -1):
                    if kw[:i] in content_lower:
                        total_weight += i / len(kw) * 0.5
                        break

        return total_weight / max(1, len(keywords))

    def _get_snippet(self, content: str, keywords: List[str], max_len: int = 200) -> str:
        """获取包含关键词的文本片段"""
        content_lower = content.lower()

        # 找到第一个匹配关键词的位置
        best_pos = -1
        for kw in keywords:
            pos = content_lower.find(kw)
            if pos != -1:
                if best_pos == -1 or pos < best_pos:
                    best_pos = pos

        if best_pos == -1:
            return content[:max_len] + "..."

        start = max(0, best_pos - max_len // 2)
        end = min(len(content), start + max_len)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet


# 全局单例
knowledge_search = KnowledgeSearch()

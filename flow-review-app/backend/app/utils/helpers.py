"""
通用工具函数
"""
import re
import hashlib
from difflib import SequenceMatcher


def generate_id(prefix: str = "") -> str:
    """生成简短ID"""
    import uuid
    uid = str(uuid.uuid4())[:8]
    return f"{prefix}_{uid}" if prefix else uid


def fuzzy_match(text1: str, text2: str) -> float:
    """模糊匹配相似度 (0-1)"""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def normalize_name(name: str) -> str:
    """标准化名称（去除空白和特殊字符）"""
    if not name:
        return ""
    return re.sub(r'[\s_\-]+', '', name.lower())


def extract_numbers(text: str) -> list:
    """从文本中提取所有数字"""
    if not text:
        return []
    return re.findall(r'\d+\.?\d*', text)


def calculate_hash(content: str) -> str:
    """计算内容哈希"""
    return hashlib.md5(content.encode()).hexdigest()

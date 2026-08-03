"""
文档解析器工厂

根据文件扩展名选择合适的解析器
"""
import os
import logging
from typing import Optional
from app.models.schemas import ParsedDocument
from app.services.parser.markdown_parser import MarkdownParser
from app.services.parser.bpmn_parser import BpmnParser
from app.services.parser.image_llm_parser import ImageLLMParser

logger = logging.getLogger(__name__)


def parse_document(file_path: str) -> ParsedDocument:
    """
    根据文件扩展名解析文档

    Args:
        file_path: 文件路径

    Returns:
        ParsedDocument: 统一的解析结果
    """
    ext = os.path.splitext(file_path)[1].lower()
    file_name = os.path.basename(file_path)
    logger.info(f"parse_document: file={file_name}, ext={ext}, path={file_path}")

    if ext == '.md':
        parser = MarkdownParser(file_path)
        return parser.parse()

    elif ext == '.bpmn':
        parser = BpmnParser(file_path)
        return parser.parse()

    elif ext == '.docx':
        # MVP阶段暂不实现完整 docx 解析，返回空结果
        from app.models.schemas import ParseError
        result = ParsedDocument(
            file_type="docx",
            file_name=os.path.basename(file_path),
            full_text="",
            warnings=["Word 文档解析器将在后续版本实现"],
        )
        try:
            with open(file_path, 'rb') as f:
                pass  # 仅验证文件可读
        except Exception as e:
            result.errors.append(ParseError(
                type="read_error",
                message=f"文件读取失败: {str(e)}",
            ))
        return result

    elif ext in ('.xlsx', '.csv'):
        result = ParsedDocument(
            file_type="excel",
            file_name=os.path.basename(file_path),
            full_text="",
            warnings=["Excel/CSV 解析器将在后续版本实现"],
        )
        return result

    elif ext in ('.png', '.jpg', '.jpeg'):
        parser = ImageLLMParser(file_path)
        return parser.parse()

    elif ext == '.vsdx':
        result = ParsedDocument(
            file_type="vsdx",
            file_name=os.path.basename(file_path),
            full_text="",
            warnings=["Visio VSDX 解析器将在后续版本实现"],
        )
        return result

    else:
        result = ParsedDocument(
            file_type="unknown",
            file_name=os.path.basename(file_path),
            full_text="",
            errors=[{"type": "unsupported", "message": f"不支持的文件格式: {ext}"}],
        )
        return result

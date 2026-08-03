"""
评审标准管理 API
"""
import uuid
import os
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import settings
from app.core.database import get_connection
from app.models.schemas import (
    KnowledgeDocResponse,
    KnowledgeListResponse,
    StandardsContentResponse,
    StandardCategoryItem,
    StandardSectionItem,
    StandardRuleItem,
)
from app.services.standards_parser import parse_standards

router = APIRouter()

STANDARDS_DIR = os.path.join(os.path.dirname(settings.UPLOAD_DIR), "knowledge_docs")
os.makedirs(STANDARDS_DIR, exist_ok=True)


@router.get("/content", response_model=StandardsContentResponse)
async def get_structured_content():
    """
    获取结构化评审标准内容。
    自动聚合所有已录入的标准文档，解析 Markdown 结构，
    合并为统一的 分类 → 章节 → 规则 层级展示。
    """
    data = parse_standards(STANDARDS_DIR)
    return _build_content_response(data)


def _build_content_response(data: dict) -> StandardsContentResponse:
    categories = []
    for cat in data.get("categories", []):
        sections = []
        for sec in cat.get("sections", []):
            rules = [
                StandardRuleItem(index=r.get("index", ""), content=r["content"])
                for r in sec.get("rules", [])
            ]
            sections.append(StandardSectionItem(title=sec["title"], rules=rules))
        categories.append(StandardCategoryItem(title=cat["title"], sections=sections))

    return StandardsContentResponse(
        title=data["title"],
        source_count=data["source_count"],
        categories=categories,
    )


@router.post("/upload", response_model=KnowledgeDocResponse)
async def upload_standard(
    title: str = "",
    doc_type: str = "standard",
    file: UploadFile = File(...),
):
    """上传评审标准文档"""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".md", ".docx", ".txt", ".json"}:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文档格式: {ext}，支持: .md, .docx, .txt, .json"
        )

    doc_id = str(uuid.uuid4())
    save_path = os.path.join(STANDARDS_DIR, f"{doc_id}{ext}")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件过大（>10MB）")

    with open(save_path, "wb") as f:
        f.write(content)

    text_content = ""
    if ext in {".md", ".txt", ".json"}:
        text_content = content.decode("utf-8", errors="ignore")
    chunk_count = max(1, len(text_content.split("\n")) // 10)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO knowledge_docs (id, title, doc_type, file_path, chunk_count)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_id, title or file.filename, doc_type, save_path, chunk_count)
    )
    conn.commit()
    conn.close()

    return KnowledgeDocResponse(
        id=doc_id,
        title=title or file.filename,
        doc_type=doc_type,
        file_path=save_path,
        chunk_count=chunk_count,
    )


@router.get("", response_model=KnowledgeListResponse)
async def list_standards(doc_type: Optional[str] = None):
    """列出所有评审标准文档"""
    conn = get_connection()
    cursor = conn.cursor()

    if doc_type:
        cursor.execute(
            "SELECT * FROM knowledge_docs WHERE doc_type = ? ORDER BY uploaded_at DESC",
            (doc_type,)
        )
    else:
        cursor.execute("SELECT * FROM knowledge_docs ORDER BY uploaded_at DESC")

    rows = cursor.fetchall()
    conn.close()

    documents = []
    for row in rows:
        documents.append(KnowledgeDocResponse(
            id=row["id"],
            title=row["title"],
            doc_type=row["doc_type"],
            file_path=row["file_path"],
            chunk_count=row["chunk_count"],
            uploaded_at=row["uploaded_at"] if row["uploaded_at"] else None,
        ))

    return KnowledgeListResponse(documents=documents, total=len(documents))


@router.delete("/{doc_id}")
async def delete_standard(doc_id: str):
    """删除评审标准文档"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM knowledge_docs WHERE id = ?", (doc_id,))
    row = cursor.fetchone()

    if row and os.path.exists(row["file_path"]):
        os.remove(row["file_path"])

    cursor.execute("DELETE FROM knowledge_docs WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

    return {"message": "文档已删除"}


@router.post("/rebuild")
async def rebuild_index():
    """重建评审标准索引"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, file_path FROM knowledge_docs")
    rows = cursor.fetchall()
    conn.close()

    updated = 0
    for row in rows:
        if os.path.exists(row["file_path"]):
            content = ""
            ext = os.path.splitext(row["file_path"])[1].lower()
            if ext in {".md", ".txt", ".json"}:
                with open(row["file_path"], "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

            chunk_count = max(1, len(content.split("\n")) // 10)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE knowledge_docs SET chunk_count = ? WHERE id = ?",
                (chunk_count, row["id"])
            )
            conn.commit()
            conn.close()
            updated += 1

    return {"message": f"索引重建完成，已更新 {updated} 个文档"}

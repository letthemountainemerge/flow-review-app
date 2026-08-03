"""
任务管理 API
"""
import uuid
import os
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from app.core.config import settings
from app.core.database import get_connection
from app.models.schemas import TaskResponse, TaskListResponse
from app.services.review.orchestrator import orchestrator

router = APIRouter()


def validate_file_extension(filename: str) -> bool:
    """验证文件扩展名"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in settings.ALLOWED_EXTENSIONS


def format_datetime(dt) -> Optional[str]:
    """格式化日期时间"""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return str(dt)


@router.post("", response_model=TaskResponse)
async def create_task(
    name: str = Form(...),
    manual_file: Optional[UploadFile] = File(None),
    diagram_file: Optional[UploadFile] = File(None),
    form_file: Optional[UploadFile] = File(None),
    requirement_file: Optional[UploadFile] = File(None),
):
    """创建评审任务（测试阶段不强制要求任何文件）"""
    # 校验文件扩展名
    files_to_check = []
    if manual_file:
        files_to_check.append(manual_file)
    if diagram_file:
        files_to_check.append(diagram_file)
    if form_file:
        files_to_check.append(form_file)
    if requirement_file:
        files_to_check.append(requirement_file)

    for f in files_to_check:
        if not validate_file_extension(f.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {os.path.splitext(f.filename)[1]}，"
                       f"支持的格式: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

    task_id = str(uuid.uuid4())

    # 保存文件
    task_dir = os.path.join(settings.UPLOAD_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    def save_file(file: UploadFile) -> str:
        """保存文件并返回路径"""
        save_path = os.path.join(task_dir, file.filename)
        content = file.file.read()
        # 验证文件大小
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件 {file.filename} 过大（>10MB），请压缩后重新上传"
            )
        with open(save_path, "wb") as f:
            f.write(content)
        return save_path

    manual_path = save_file(manual_file) if manual_file else None
    diagram_path = save_file(diagram_file) if diagram_file else None
    form_path = save_file(form_file) if form_file else None
    requirement_path = save_file(requirement_file) if requirement_file else None

    # 保存到数据库
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO review_tasks (id, name, status, created_at, manual_file, diagram_file, form_file, requirement_file)
           VALUES (?, ?, 'pending', datetime('now', 'localtime'), ?, ?, ?, ?)""",
        (task_id, name, manual_path, diagram_path, form_path, requirement_path)
    )
    conn.commit()
    conn.close()

    return TaskResponse(
        id=task_id,
        name=name,
        status="pending",
        manual_file=manual_file.filename if manual_file else None,
        diagram_file=diagram_file.filename if diagram_file else None,
        form_file=form_file.filename if form_file else None,
        requirement_file=requirement_file.filename if requirement_file else None,
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """查询任务列表"""
    conn = get_connection()

    # 1. 先查询总数
    if status:
        total_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM review_tasks WHERE status = ?",
            (status,)
        ).fetchone()
    else:
        total_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM review_tasks"
        ).fetchone()
    total = total_row["cnt"]

    # 2. 查询分页数据
    if status:
        cursor = conn.execute(
            "SELECT * FROM review_tasks WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, page_size, (page - 1) * page_size)
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM review_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, (page - 1) * page_size)
        )
    rows = cursor.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        tasks.append(TaskResponse(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            created_at=format_datetime(row["created_at"]),
            completed_at=format_datetime(row["completed_at"]),
            manual_file=os.path.basename(row["manual_file"]) if row["manual_file"] else None,
            diagram_file=os.path.basename(row["diagram_file"]) if row["diagram_file"] else None,
            form_file=os.path.basename(row["form_file"]) if row["form_file"] else None,
            requirement_file=os.path.basename(row["requirement_file"]) if row["requirement_file"] else None,
        ))

    return TaskListResponse(tasks=tasks, total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM review_tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskResponse(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        created_at=format_datetime(row["created_at"]),
        completed_at=format_datetime(row["completed_at"]),
        manual_file=os.path.basename(row["manual_file"]) if row["manual_file"] else None,
        diagram_file=os.path.basename(row["diagram_file"]) if row["diagram_file"] else None,
        form_file=os.path.basename(row["form_file"]) if row["form_file"] else None,
        requirement_file=os.path.basename(row["requirement_file"]) if row["requirement_file"] else None,
    )


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM review_tasks WHERE id = ?", (task_id,))
    cursor.execute("DELETE FROM review_history WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()

    # 清理文件
    task_dir = os.path.join(settings.UPLOAD_DIR, task_id)
    if os.path.exists(task_dir):
        import shutil
        shutil.rmtree(task_dir)

    return {"message": "任务已删除"}


@router.post("/{task_id}/review")
async def start_review(task_id: str, background_tasks: BackgroundTasks):
    """启动评审"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM review_tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")
    if row["status"] == "reviewing":
        raise HTTPException(status_code=400, detail="任务正在评审中")

    # 更新状态为 reviewing，然后后台执行评审
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE review_tasks SET status = 'reviewing' WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()

    def _run_review():
        """后台执行评审"""
        try:
            orchestrator.execute_review(task_id)
        except Exception as e:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE review_tasks SET status = 'failed' WHERE id = ?",
                (task_id,)
            )
            conn.commit()
            conn.close()
            import logging
            logging.getLogger(__name__).error(f"后台评审失败: {e}")

    background_tasks.add_task(_run_review)

    return {
        "message": "评审已启动，正在后台处理中",
        "task_id": task_id,
        "status": "reviewing",
    }


@router.get("/{task_id}/report")
async def get_report(task_id: str):
    """获取评审报告"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT report FROM review_tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not row["report"]:
        raise HTTPException(status_code=404, detail="报告未生成")

    return json.loads(row["report"])


@router.post("/{task_id}/feedback")
async def submit_feedback(task_id: str, feedback: dict):
    """提交专家反馈"""
    conn = get_connection()
    cursor = conn.cursor()

    feedback_id = str(uuid.uuid4())
    cursor.execute(
        """INSERT INTO review_history (id, task_id, dimension_id, finding_id,
           ai_conclusion, expert_correction, correction_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            feedback_id, task_id,
            feedback.get("dimension_id", 0),
            feedback.get("finding_id", ""),
            feedback.get("ai_conclusion", ""),
            feedback.get("expert_comment", ""),
            feedback.get("correction_type", ""),
        )
    )
    conn.commit()
    conn.close()

    return {"message": "反馈已提交", "feedback_id": feedback_id}


@router.get("/{task_id}/feedback")
async def get_feedback(task_id: str):
    """获取反馈记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM review_history WHERE task_id = ? ORDER BY corrected_at DESC",
        (task_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    feedbacks = []
    for row in rows:
        feedbacks.append({
            "id": row["id"],
            "task_id": row["task_id"],
            "dimension_id": row["dimension_id"],
            "finding_id": row["finding_id"],
            "ai_conclusion": row["ai_conclusion"],
            "expert_correction": row["expert_correction"],
            "correction_type": row["correction_type"],
            "corrected_at": format_datetime(row["corrected_at"]),
        })

    return {"feedbacks": feedbacks, "total": len(feedbacks)}

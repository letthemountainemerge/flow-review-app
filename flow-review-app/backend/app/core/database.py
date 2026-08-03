"""
数据库初始化和管理
"""
import sqlite3
import os
import uuid
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# 项目根目录（backend/ 目录）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_path() -> str:
    """获取数据库文件路径（始终解析为绝对路径，避免多实例问题）"""
    db_url = settings.DATABASE_URL
    # sqlite:///./data/sqlite/flow_review.db -> ./data/sqlite/flow_review.db
    db_path = db_url.replace("sqlite:///", "")

    # 如果是相对路径，基于 backend/ 目录解析为绝对路径
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(os.path.join(_BACKEND_DIR, db_path))

    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    logger.info(f"数据库路径: {db_path}")
    return db_path


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30)  # 30秒超时，防止长时间阻塞
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # WAL模式支持并发读写
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 评审任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_tasks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            completed_at TIMESTAMP,
            manual_file TEXT,
            diagram_file TEXT,
            form_file TEXT,
            requirement_file TEXT,
            parsed_data TEXT,
            report TEXT,
            expert_feedback TEXT
        )
    """)

    # 知识库文档表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 评审历史记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_history (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            dimension_id INTEGER NOT NULL,
            finding_id TEXT NOT NULL,
            ai_conclusion TEXT,
            expert_correction TEXT,
            correction_type TEXT,
            corrected_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 初始化默认评审标准（仅当 knowledge_docs 表为空时）
    cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_docs")
    count = cursor.fetchone()["cnt"]
    if count == 0:
        _seed_default_standard(cursor)

    conn.commit()
    conn.close()


def _seed_default_standard(cursor):
    """写入默认的流程图评审标准种子数据"""
    seed_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "seed_review_standard.md"
    )
    if not os.path.exists(seed_file):
        return

    knowledge_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "knowledge_docs"
    )
    os.makedirs(knowledge_dir, exist_ok=True)

    doc_id = str(uuid.uuid4())
    dest_path = os.path.join(knowledge_dir, f"{doc_id}.md")

    # 复制种子文件到 knowledge_docs 目录
    with open(seed_file, "r", encoding="utf-8") as src:
        content = src.read()
    with open(dest_path, "w", encoding="utf-8") as dst:
        dst.write(content)

    chunk_count = max(1, len(content.split("\n")) // 10)

    cursor.execute(
        """INSERT INTO knowledge_docs (id, title, doc_type, file_path, chunk_count)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_id, "流程图评审标准", "standard", dest_path, chunk_count)
    )

"""
流程文件智能评审系统 - FastAPI 主入口
"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import tasks, standards, settings
from app.core.database import init_db, get_connection

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="流程文件智能评审系统",
    description="AI辅助流程文件评审工具",
    version="0.1.0",
)

# CORS 配置（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务管理"])
app.include_router(standards.router, prefix="/api/standards", tags=["评审标准管理"])
app.include_router(settings.router, prefix="/api/settings", tags=["系统设置"])


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()
    logger.info(f"数据库初始化完成")

    # 重置启动时卡在中间状态的任务（reviewing/parsing 超过 10 分钟）
    _reset_stuck_tasks()


def _reset_stuck_tasks():
    """将卡在 reviewing/parsing 状态的任务标记为 failed"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE review_tasks
            SET status = 'failed'
            WHERE status IN ('reviewing', 'parsing')
              AND created_at < datetime('now', 'localtime', '-10 minutes')
        """)
        if cursor.rowcount > 0:
            logger.warning(f"重置了 {cursor.rowcount} 个卡住的评审任务为 failed")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"重置卡住任务失败: {e}")


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}

"""
评审编排器

负责协调文档解析 + 多维度评审流程
"""
import json
import os
import logging
from typing import List, Optional
from datetime import datetime

from app.core.database import get_connection
from app.core.config import settings
from app.models.schemas import (
    ParsedDocument, ReviewReport, DimensionResult, Finding,
    TaskResponse
)
from app.services.parser.parser_factory import parse_document
from app.services.review.dimension2 import Dimension2Review
from app.services.review.dimension5 import Dimension5Review
from app.utils.helpers import generate_id

logger = logging.getLogger(__name__)


class ReviewOrchestrator:
    """评审编排器"""

    def __init__(self):
        self.dim2_reviewer = Dimension2Review()
        self.dim5_reviewer = Dimension5Review()

    def execute_review(self, task_id: str) -> ReviewReport:
        """执行完整评审流程"""
        # 1. 获取任务信息
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM review_tasks WHERE id = ?",
            (task_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise ValueError(f"任务 {task_id} 不存在")

        # 2. 更新状态为解析中
        cursor.execute(
            "UPDATE review_tasks SET status = 'parsing' WHERE id = ?",
            (task_id,)
        )
        conn.commit()

        manual_path = row["manual_file"]
        diagram_path = row["diagram_file"]

        # 3. 解析文档
        try:
            manual_doc = parse_document(manual_path) if manual_path else None
            diagram_doc = parse_document(diagram_path) if diagram_path else None
        except Exception as e:
            cursor.execute(
                "UPDATE review_tasks SET status = 'failed' WHERE id = ?",
                (task_id,)
            )
            conn.commit()
            conn.close()
            raise RuntimeError(f"文档解析失败: {str(e)}")

        # 保存解析结果
        if manual_doc or diagram_doc:
            parsed_data = json.dumps({
                "manual": manual_doc.model_dump() if manual_doc else None,
                "diagram": diagram_doc.model_dump() if diagram_doc else None,
            }, ensure_ascii=False, default=str)

            cursor.execute(
                "UPDATE review_tasks SET status = 'reviewing', parsed_data = ? WHERE id = ?",
                (parsed_data, task_id)
            )
            conn.commit()

        # 4. 执行各维度评审（MVP: 维度2 + 维度5）
        dimension_results: List[DimensionResult] = []

        try:
            # 维度2: 角色职责匹配
            if manual_doc and diagram_doc:
                try:
                    dim2_result = self.dim2_reviewer.review(manual_doc, diagram_doc)
                    dimension_results.append(dim2_result)
                    logger.info(f"[task={task_id}] 维度2评审完成: {dim2_result.conclusion} ({dim2_result.score}分)")
                except Exception as e:
                    logger.error(f"[task={task_id}] 维度2评审失败: {type(e).__name__}: {e}", exc_info=True)

            # 维度5: 流程图规范检查
            if diagram_doc:
                try:
                    dim5_result = self.dim5_reviewer.review(diagram_doc)
                    dimension_results.append(dim5_result)
                    logger.info(f"[task={task_id}] 维度5评审完成: {dim5_result.conclusion} ({dim5_result.score}分)")
                except Exception as e:
                    logger.error(f"[task={task_id}] 维度5评审失败: {type(e).__name__}: {e}", exc_info=True)

        except Exception as e:
            # 记录整体评审异常（不太可能发生，但保留作为安全网）
            logger.error(f"[task={task_id}] 评审编排异常: {type(e).__name__}: {e}", exc_info=True)

        # 5. 计算总体得分
        if dimension_results:
            overall_score = int(
                sum(d.score for d in dimension_results) / len(dimension_results)
            )
        else:
            overall_score = 0

        # 6. 生成总评
        has_fail = any(d.conclusion == "不通过" for d in dimension_results)
        has_concern = any(d.conclusion == "需关注" for d in dimension_results)
        has_unreviewable = any(d.conclusion == "无法评审" for d in dimension_results)

        if has_unreviewable:
            overall_conclusion = "无法评审"
        elif has_fail:
            overall_conclusion = "不通过"
        elif has_concern:
            overall_conclusion = "需关注"
        elif overall_score >= 80:
            overall_conclusion = "通过"
        else:
            overall_conclusion = "需关注"

        # 7. 生成摘要
        summaries = []
        for dim in dimension_results:
            summaries.append(
                f"维度{dim.dimension_id}「{dim.dimension_name}」: "
                f"{dim.conclusion}（{dim.score}分）- 发现{dim.findings.__len__()}个问题"
            )

        review_report = ReviewReport(
            task_id=task_id,
            overall_conclusion=overall_conclusion,
            overall_score=overall_score,
            dimension_results=dimension_results,
            summary="\n".join(summaries),
        )

        # 8. 保存报告
        report_json = json.dumps(
            review_report.model_dump(), ensure_ascii=False, default=str
        )
        cursor.execute(
            """UPDATE review_tasks
               SET status = 'completed', completed_at = datetime('now', 'localtime'), report = ?
               WHERE id = ?""",
            (report_json, task_id)
        )
        conn.commit()
        conn.close()

        return review_report


# 全局单例
orchestrator = ReviewOrchestrator()

"""
端到端评审流程测试
"""
import os
import sys
import json
import uuid

# 设置环境
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 初始化数据库
from app.core.database import init_db
init_db()

from app.services.parser.parser_factory import parse_document
from app.services.review.orchestrator import orchestrator
from app.core.database import get_connection

print("=" * 60)
print("流程文件智能评审系统 - 端到端测试")
print("=" * 60)

# Step 1: 创建测试任务
task_id = str(uuid.uuid4())
manual_path = os.path.join("data", "test_manual.md")
diagram_path = os.path.join("data", "test_diagram.bpmn")

print(f"\n[Step 1] 创建测试任务: {task_id[:8]}...")
print(f"  说明书: {manual_path}")
print(f"  流程图: {diagram_path}")

conn = get_connection()
cursor = conn.cursor()
cursor.execute(
    """INSERT INTO review_tasks (id, name, status, manual_file, diagram_file)
       VALUES (?, ?, 'pending', ?, ?)""",
    (task_id, "采购审批流程测试", manual_path, diagram_path)
)
conn.commit()
conn.close()
print("  ✅ 任务创建成功")

# Step 2: 测试文档解析
print("\n[Step 2] 测试文档解析")
print("-" * 40)

manual_doc = parse_document(manual_path)
diagram_doc = parse_document(diagram_path)

print(f"  说明书:")
print(f"    章节: {len(manual_doc.sections)}")
print(f"    角色: {len(manual_doc.role_table)}")
print(f"    活动: {len(manual_doc.activity_table)}")
print(f"    风险: {len(manual_doc.risk_table)}")
print(f"    KPI: {len(manual_doc.kpi_table)}")
print(f"    警告: {manual_doc.warnings}")
print(f"    错误: {manual_doc.errors}")

print(f"  流程图:")
print(f"    节点: {len(diagram_doc.nodes)}")
print(f"    连线: {len(diagram_doc.edges)}")
print(f"    泳道: {len(diagram_doc.swimlanes)}")
print(f"    KCP: {diagram_doc.kcp_nodes}")
print(f"    警告: {diagram_doc.warnings}")
print(f"    错误: {diagram_doc.errors}")

# Step 3: 执行评审
print("\n[Step 3] 执行评审")
print("-" * 40)

try:
    report = orchestrator.execute_review(task_id)
    print(f"  总体结论: {report.overall_conclusion}")
    print(f"  总体得分: {report.overall_score}/100")
    print(f"  评审维度数: {len(report.dimension_results)}")

    for dim in report.dimension_results:
        print(f"\n  维度{dim.dimension_id}: {dim.dimension_name}")
        print(f"    结论: {dim.conclusion}")
        print(f"    得分: {dim.score}/100")
        print(f"    发现项: {len(dim.findings)}")
        for finding in dim.findings:
            print(f"      [{finding.severity}] {finding.description[:80]}...")
            if finding.suggestion:
                print(f"        → 建议: {finding.suggestion[:80]}")

except Exception as e:
    print(f"  ❌ 评审失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: 验证数据库状态
print("\n[Step 4] 验证数据库状态")
print("-" * 40)

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT status, report FROM review_tasks WHERE id = ?", (task_id,))
row = cursor.fetchone()
conn.close()

if row:
    print(f"  状态: {row['status']}")
    print(f"  有报告: {bool(row['report'])}")
    if row['report']:
        r = json.loads(row['report'])
        print(f"  报告概要: {r.get('summary', '')[:100]}")
    print("  ✅ 数据库状态正确")
else:
    print("  ❌ 未找到任务记录")
    sys.exit(1)

# Step 5: 清理测试数据
print("\n[Step 5] 清理测试数据")
conn = get_connection()
cursor = conn.cursor()
cursor.execute("DELETE FROM review_tasks WHERE id = ?", (task_id,))
cursor.execute("DELETE FROM review_history WHERE task_id = ?", (task_id,))
conn.commit()
conn.close()
print("  ✅ 测试数据已清理")

print("\n" + "=" * 60)
print("✅ 所有测试通过！")
print("=" * 60)

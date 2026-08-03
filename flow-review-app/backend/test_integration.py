"""
集成测试脚本

用法:
1. 先启动后端: cd backend && source venv/bin/activate && uvicorn app.main:app --port 8000
2. 再运行此脚本: python test_integration.py
"""
import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"
MANUAL_FILE = os.path.join("data", "test_manual.md")
DIAGRAM_FILE = os.path.join("data", "test_diagram.bpmn")

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        print(f"\n{'='*50}")
        print(f"[测试] {name}")
        print(f"{'='*50}")
        fn()
        passed += 1
        print(f"✅ {name} - 通过")
    except Exception as e:
        failed += 1
        print(f"❌ {name} - 失败: {e}")

def test_health():
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print(f"  服务状态: {r.json()}")

def test_create_task():
    with open(MANUAL_FILE, "rb") as f1, open(DIAGRAM_FILE, "rb") as f2:
        r = requests.post(f"{BASE_URL}/api/tasks", files={
            "name": (None, "集成测试-采购审批"),
            "manual_file": ("manual.md", f1, "text/markdown"),
            "diagram_file": ("diagram.bpmn", f2, "application/xml"),
        })
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"
    print(f"  任务ID: {data['id']}")
    print(f"  说明书: {data['manual_file']}")
    print(f"  流程图: {data['diagram_file']}")
    return data["id"]

def test_list_tasks():
    r = requests.get(f"{BASE_URL}/api/tasks")
    assert r.status_code == 200
    data = r.json()
    assert "tasks" in data
    assert "total" in data
    print(f"  任务总数: {data['total']}")

def test_start_review(task_id):
    r = requests.post(f"{BASE_URL}/api/tasks/{task_id}/review")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    print(f"  评审结果: {data['overall_conclusion']}")
    print(f"  总体得分: {data['overall_score']}")

def test_get_report(task_id):
    r = requests.get(f"{BASE_URL}/api/tasks/{task_id}/report")
    assert r.status_code == 200
    data = r.json()
    assert "dimension_results" in data
    print(f"  评审维度数: {len(data['dimension_results'])}")
    for dim in data["dimension_results"]:
        print(f"    维度{dim['dimension_id']}: {dim['conclusion']} ({dim['score']}分)")
        print(f"      发现项: {len(dim['findings'])}")

def test_submit_feedback(task_id):
    r = requests.post(f"{BASE_URL}/api/tasks/{task_id}/feedback", json={
        "finding_id": "test_finding_1",
        "dimension_id": 2,
        "correction_type": "confirmed",
        "expert_comment": "AI评审正确，已确认",
        "ai_conclusion": "confirmed",
    })
    assert r.status_code == 200
    print(f"  反馈: {r.json()}")

def test_knowledge_upload():
    with open(MANUAL_FILE, "rb") as f:
        r = requests.post(f"{BASE_URL}/api/knowledge/upload", files={
            "file": ("standard.md", f, "text/markdown"),
        }, data={"title": "测试标准文档", "doc_type": "standard"})
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    print(f"  文档ID: {data['id']}")
    print(f"  分片数: {data['chunk_count']}")
    return data["id"]

def test_knowledge_list():
    r = requests.get(f"{BASE_URL}/api/knowledge")
    assert r.status_code == 200
    data = r.json()
    print(f"  文档总数: {data['total']}")

def test_delete_task(task_id):
    r = requests.delete(f"{BASE_URL}/api/tasks/{task_id}")
    assert r.status_code == 200
    print(f"  删除: {r.json()}")

if __name__ == "__main__":
    print("=" * 60)
    print("流程文件智能评审系统 - HTTP集成测试")
    print("=" * 60)

    # 1. 健康检查
    test("健康检查", test_health)

    # 2. 创建任务
    task_id = None
    def _create():
        nonlocal task_id
        task_id = test_create_task()
    test("创建评审任务", _create)

    # 3. 任务列表
    test("任务列表查询", test_list_tasks)

    # 4. 启动评审
    def _review():
        test_start_review(task_id)
    test("启动评审", _review)

    # 5. 获取报告
    def _report():
        test_get_report(task_id)
    test("获取评审报告", _report)

    # 6. 提交反馈
    def _feedback():
        test_submit_feedback(task_id)
    test("提交专家反馈", _feedback)

    # 7. 知识库
    test("知识库上传", lambda: test_knowledge_upload())
    test("知识库列表", test_knowledge_list)

    # 8. 清理任务
    if task_id:
        test("删除任务", lambda: test_delete_task(task_id))

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败, {passed + failed} 总计")
    print("=" * 60)

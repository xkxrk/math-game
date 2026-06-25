"""冒烟测试：使用 TestClient 在进程内验证 API。"""
import sys
import os

# 确保能导入 backend 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test(name, response):
    status = "PASS" if response.status_code == 200 else f"FAIL({response.status_code})"
    print(f"[{status}] {name}")
    if response.status_code == 200:
        import json
        data = response.json()
        print(f"  -> {json.dumps(data, ensure_ascii=False)[:200]}")
    else:
        print(f"  -> {response.text[:200]}")
    return response.status_code == 200


print("=== 冒烟测试开始 ===\n")

# 1. 健康检查
r = client.get("/api/health")
test("GET /api/health", r)

# 2. 规则
r = client.get("/api/rules")
test("GET /api/rules", r)

# 3. 历史数据
r = client.get("/api/history?limit=3")
test("GET /api/history", r)

# 4. 最新一期
r = client.get("/api/latest")
test("GET /api/latest", r)

# 5. 统计
r = client.get("/api/stats?limit=50")
test("GET /api/stats", r)

# 6. 后台状态
r = client.get("/api/admin/status")
test("GET /api/admin/status", r)

# 7. 预测（启发式，因为没配 API Key）
r = client.post("/api/predict?count=1")
test("POST /api/predict", r)

# 8. 预测记录列表
r = client.get("/api/predictions?limit=5")
test("GET /api/predictions", r)

# 9. 回测评估
r = client.post("/api/evaluate")
test("POST /api/evaluate", r)

# 10. 后台登录
r = client.post("/api/admin/login", json={"username": "admin", "password": "admin"})
test("POST /api/admin/login", r)
login_cookie = r.cookies

# 11. 登录后状态
r = client.get("/api/admin/status")
test("GET /api/admin/status (after login)", r)

print("\n=== 冒烟测试完成 ===")

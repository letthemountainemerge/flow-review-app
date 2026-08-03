# 流程文件智能评审系统

基于AI的流程文件评审辅助工具，支持8个维度自动评审。

## 启动

### 后端
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

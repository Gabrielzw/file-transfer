# 文件中转站（Vue3 + FastAPI）

实现内容（v1.0）：
- 管理员登录（JWT）
- 单文件上传（进度可见）
- 文件列表/删除
- 生成分享链接（有效期/可选提取码/可选下载次数上限）
- 访客下载页（提取码校验 + 下载 Token）

## 本地开发

### 后端

1) 复制并填写配置：
- `backend/.env.example` -> `backend/.env`

2) 启动：
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认通过 Vite Proxy 访问后端 `/api`（目标 `http://localhost:8003`）。

## Docker Compose 部署

1) 复制并填写配置：
- `.env.example` -> `.env`

2) 启动：
```bash
docker compose up -d --build
```

访问：
- 管理后台：`http://localhost:5273/admin/login`
- 分享页：`http://localhost:5273/s/<share_code>`

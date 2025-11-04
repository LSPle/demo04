# MySQL 数据库优化平台

一个基于 Vue 3 + Ant Design Vue + Vite（前端）与 Flask（后端）的数据库性能监控与优化平台。提供实例管理、实例概览、SQL 控制台、SQL 优化、架构优化、配置优化等功能。

## 功能特性
- 🔐 用户认证：登录/登出与会话管理
- 🗄️ 实例管理：添加、编辑、删除 MySQL 实例，实时连接状态检测
- 🧭 实例概览：实例列表与运行状态汇总
- 💻 SQL 控制台：在线执行 SQL、查看数据库结构、查询历史
- 🔍 SQL 优化：分析 SQL 性能并给出优化建议
- 🏗️ 架构优化：性能指标、复制状态、慢日志等健康检查
- ⚙️ 配置优化：分析 MySQL 配置参数并给出调优建议

## 技术栈
**前端**
- Vue 3
- Ant Design Vue 4
- Vite 5
- Vue Router 4

**后端**
- Flask 2.3
- Flask-SQLAlchemy、Flask-JWT-Extended、Flask-RESTful、Flask-CORS
- PyMySQL、SQLAlchemy、sqlparse、requests

**数据库**
- MySQL 5.7/8.0

## 项目结构
```
├── backend/                    # 后端 Flask 应用
│  ├── app/                     # 应用代码（models/routes/services/utils 等）
│  │  └── wsgi.py               # 生产入口（Gunicorn 加载 app.wsgi:app）
│  ├── requirements.txt         # 后端依赖
│  └── run.py                   # 开发启动入口（默认端口 5000）
├── front/                      # 前端 Vue 应用
│  ├── src/
│  │  ├── pages/                # 页面组件（Vue）
│  │  │  ├── Login.vue
│  │  │  ├── InstanceOverview.vue
│  │  │  ├── InstanceManagement.vue
│  │  │  ├── SQLConsole.vue
│  │  │  ├── SQLOptimization.vue
│  │  │  ├── ArchitectureOptimization.vue
│  │  │  └── ConfigOptimization.vue
│  ├── package.json             # 前端脚本与依赖
│  └── vite.config.js           # Vite 配置（默认端口 3000）
├── README.md                   # 项目说明
└── .env.sample                 # 环境变量样例（目前已注释，仅作参考）
```

## 配置说明（后端）
- 统一配置集中在 `backend/app/config.py`（不依赖 .env）：
  - `SECRET_KEY`、`JWT_SECRET_KEY`
  - `SQLALCHEMY_DATABASE_URI`（由 MySQL 连接信息计算）
  - `DEEPSEEK_*`（API Key/模型/超时/开关）
- `backend/.env` 与根目录 `.env.sample` 已整行注释，保留参考，不参与运行。
- 如需修改数据库或 LLM 参数，直接调整 `Config` 类中的常量即可。

## 环境要求
- Node.js 16+
- Python 3.8+
- MySQL 5.7+/8.0+

## 安装与启动（开发）
1) 安装依赖
```bash
# 前端依赖
cd front
npm install

# 后端依赖
cd ../backend
pip install -r requirements.txt
```

2) 启动后端（默认端口 5000）
```bash
cd backend
python run.py
# 可通过环境变量覆盖端口（PowerShell）：
# $env:PORT=5001; python run.py
```

3) 启动前端（默认端口 3000）
```bash
cd front
npm run dev
```
- 前端地址：`http://localhost:3000/`
- 后端地址：`http://localhost:5000/`

前端请求后端的方式：
- `front/src/config/api.js` 使用 `VITE_API_BASE_URL`，未设置时默认 `http://localhost:5000`。
- 如果你偏好使用 Vite 代理（相对路径 `/api`），请将 `front/vite.config.js` 中的 `proxy.target` 改为 `http://localhost:5000`（当前示例为 5002，仅示例）。

示例（将代理改为 5000）：
```js
export default defineConfig({
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  }
});
```

## 生产部署（Docker）
- 根目录 `Dockerfile` 使用多阶段构建，最终用 Gunicorn 启动：`app.wsgi:app`
- 默认监听 `8080` 端口（`EXPOSE 8080`），可通过容器映射到外部。
```bash
docker build -t mysql-optimizer .
docker run -p 8080:8080 mysql-optimizer
```

## 常见问题
- 端口被占用：
  - Windows 查询端口：`netstat -ano | findstr :3000` 或 `:5000`
  - 结束进程：`taskkill /F /PID <PID>`
- 前端无法请求后端：
  - 确认后端已在 `5000` 端口启动，或在前端设置 `VITE_API_BASE_URL`
  - 若使用代理，请同步修改 `proxy.target`
- 数据库连接失败：
  - 检查 `backend/app/config.py` 中 MySQL 连接信息是否正确、网络是否可达、权限是否足够
- DeepSeek 不生效：
  - 确认 `DEEPSEEK_API_KEY` 已配置且 `LLM_ENABLED = True`

## 许可协议
MIT License

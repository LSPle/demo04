# MySQL 数据库优化平台

一个基于 Vue 3 + Ant Design Vue + Vite（前端）与 Flask（后端）的数据库性能监控与优化平台。提供实例管理、实例概览、SQL 控制台、SQL 优化、架构优化、配置优化等功能，支持一键同时启动前后端进行开发。

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
│  ├── requirements.txt         # 后端依赖
│  └── run.py                   # 开发启动入口（默认端口 5002）
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
└── .env.sample                 # 环境变量样例（如需）
```

## 环境要求
- Node.js 16+
- Python 3.8+
- MySQL 5.7+/8.0+

## 安装与启动
1) 安装依赖
```bash
# 前端依赖
cd front
npm install

# 后端依赖
cd ../backend
pip install -r requirements.txt
```

2) 启动（推荐：一键同时启动前后端）
```bash
cd front
npm run dev
```
- 前端地址：`http://localhost:3000/`
- 后端地址：`http://localhost:5002/`

3) 启动（分别启动）
```bash
# 后端（在 backend 目录）
python run.py

# 前端（在 front 目录）
npm run frontend  # 或者直接运行：vite
```

## 端口与代理
- 前端端口在 `front/vite.config.js` 中配置：
```js
export default defineConfig({
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true,
      }
    }
  }
});
```
- 代理：开发环境下，`/api` 会被代理到后端 `http://localhost:5002`。

## 常见问题
- 端口被占用：
  - Windows 查询端口：`netstat -ano | findstr :3000`
  - 结束进程：`taskkill /F /PID <PID>`
- 自动切换端口：若想让前端在端口被占用时自动选择备用端口，设置 `strictPort: false`。

## 许可协议
MIT License

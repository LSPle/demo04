# MySQL 数据库优化平台

一个专业的 MySQL 数据库性能监控与优化平台，基于 React + Flask 架构，提供完整的数据库管理、性能分析和智能优化解决方案。

## 功能特性

- 🔐 **用户认证系统**: 完整的用户注册、登录和会话管理
- 🗄️ **实例管理**: MySQL 数据库实例的添加、编辑、删除和连接状态监控
- 💻 **SQL 控制台**: 在线 SQL 查询执行器，支持数据库结构查看和历史查询
- 🔍 **SQL 优化**: 基于 AI 的 SQL 查询优化建议和性能分析
- 🏗️ **架构优化**: 数据库架构分析、复制状态检查和慢查询日志分析
- ⚙️ **配置优化**: MySQL 配置参数分析和优化建议
- 📊 **实时监控**: WebSocket 实现的实例状态实时更新
- 🎯 **智能诊断**: 基于规则和 AI 的数据库健康检查

## 技术栈

### 前端
- **React 18.2.0** - 现代化的用户界面框架
- **Ant Design 5.2.0** - 企业级 UI 设计语言和组件库
- **React Router 6.8.0** - 单页应用路由管理
- **Socket.IO Client 4.7.2** - 实时双向通信

### 后端
- **Flask 2.3.3** - 轻量级 Python Web 框架
- **Flask-SQLAlchemy 3.0.5** - ORM 数据库操作
- **Flask-JWT-Extended 4.5.3** - JWT 身份认证
- **Flask-SocketIO 5.3.6** - WebSocket 实时通信
- **PyMySQL 1.1.0** - MySQL 数据库连接器
- **SQLParse 0.4.4** - SQL 语句解析
- **Requests 2.32.3** - HTTP 客户端（AI API 调用）

### 数据库
- **MySQL** - 主要支持的数据库系统
- **SQLite** - 用户数据和配置存储

### 部署
- **Docker** - 容器化部署
- **Gunicorn 21.2.0** - WSGI HTTP 服务器

## 快速开始

### 环境要求

- Node.js 16+ 
- Python 3.8+
- MySQL 5.7+ 或 8.0+

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd database-optimization-platform
   ```

2. **配置环境变量**
   ```bash
   cp .env.sample .env
   # 编辑 .env 文件，配置数据库连接和 API 密钥
   ```

3. **安装依赖**
   ```bash
   # 安装前端依赖
   cd front
   npm install
   
   # 安装后端依赖
   cd ../backend
   pip install -r requirements.txt
   ```

4. **启动应用**
   
   **方式一：分别启动（开发模式）**
   ```bash
   # 启动后端（在 backend 目录）
   python run.py
   
   # 启动前端（在 front 目录）
   npm start
   ```
   
   **方式二：一键启动（推荐）**
   ```bash
   # 在 front 目录下执行
   npm run dev
   ```

5. **访问应用**
   - 前端地址：http://localhost:3000
   - 后端 API：http://localhost:5000

### 配置说明

在 `.env` 文件中配置以下参数：

```env
# 数据库配置
DATABASE_URL=sqlite:///app.db

# JWT 密钥
JWT_SECRET_KEY=your-secret-key

# AI API 配置（可选）
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_URL=https://api.deepseek.com

# 其他配置
FLASK_ENV=development
```

### 运行测试

```bash
npm test
```

## 项目结构

```
├── backend/                    # 后端 Flask 应用
│   ├── app/                   # 应用核心代码
│   │   ├── models/           # 数据模型
│   │   ├── routes/           # API 路由
│   │   ├── services/         # 业务逻辑服务
│   │   └── utils/            # 工具函数
│   ├── requirements.txt      # Python 依赖
│   ├── run.py               # 应用启动文件
│   └── Dockerfile           # 后端容器配置
├── front/                     # 前端 React 应用
│   ├── src/
│   │   ├── components/       # 可复用组件
│   │   ├── contexts/         # React Context
│   │   ├── pages/           # 页面组件
│   │   │   ├── Login.js     # 登录页面
│   │   │   ├── InstanceManagement.js  # 实例管理
│   │   │   ├── SQLConsole.js          # SQL 控制台
│   │   │   ├── SQLOptimization.js     # SQL 优化
│   │   │   ├── ArchitectureOptimization.js  # 架构优化
│   │   │   └── ConfigOptimization.js        # 配置优化
│   │   ├── utils/           # 工具函数
│   │   └── styles/          # 样式文件
│   ├── package.json         # 前端依赖配置
│   └── public/              # 静态资源
├── .env.sample              # 环境变量模板
├── Dockerfile               # 整体容器配置
└── README.md               # 项目说明文档
```

## 主要功能模块

### 🔐 用户认证
- 用户注册和登录
- JWT Token 身份验证
- 会话管理和自动登出

### 🗄️ 实例管理
- 添加、编辑、删除 MySQL 实例
- 实时连接状态监控
- 批量操作支持

### 💻 SQL 控制台
- 在线 SQL 查询执行
- 数据库结构浏览（库、表、字段、索引）
- 查询历史记录
- 表结构详细信息查看

### 🔍 SQL 优化
- AI 驱动的 SQL 查询分析
- 性能优化建议
- 执行计划解读

### 🏗️ 架构优化
- 数据库架构健康检查
- 复制状态监控
- 慢查询日志分析
- 风险项识别和建议

### ⚙️ 配置优化
- MySQL 配置参数分析
- 性能调优建议
- 配置对比和推荐值

### 📊 实时监控
- WebSocket 实现的状态实时更新
- 实例连接状态变化通知
- 自动刷新和状态同步

## 开发说明

### 开发环境设置

1. **前端开发**
   ```bash
   cd front
   npm start          # 启动开发服务器
   npm run build      # 构建生产版本
   npm test           # 运行测试
   ```

2. **后端开发**
   ```bash
   cd backend
   python run.py      # 启动 Flask 开发服务器
   ```

3. **同时开发前后端**
   ```bash
   cd front
   npm run dev        # 同时启动前后端服务
   ```

### 项目特性

- **响应式设计**: 支持桌面和移动设备
- **实时通信**: WebSocket 实现状态实时更新
- **AI 集成**: 支持 DeepSeek API 进行智能分析
- **安全认证**: JWT Token 身份验证机制
- **容器化部署**: Docker 支持一键部署
- **模块化架构**: 前后端分离，易于维护和扩展

### 注意事项

- 确保 MySQL 实例可访问且权限配置正确
- AI 功能需要配置 DeepSeek API 密钥
- 生产环境请修改默认的 JWT 密钥
- 建议使用 HTTPS 协议保障数据安全

## 许可证

MIT License
"""WSGI 入口文件（生产部署使用）
- 作用：创建并暴露 Flask 应用对象 `app`，让 WSGI 服务器（如 Gunicorn）加载。
- 启动方式：Dockerfile 使用命令 `gunicorn app.wsgi:app`，即到本文件取名为 `app` 的对象。
- 开发区分：本地开发用 `backend/run.py`；生产环境用本文件作为入口。
"""

# 从应用工厂导入创建函数
from . import create_app

# 创建并暴露 WSGI 应用对象（供服务器加载）
app = create_app()

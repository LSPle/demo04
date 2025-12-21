import os
from urllib.parse import quote_plus

# 管理并加载后端应用配置

class Config:
    SECRET_KEY = "student-demo-secret-key-2024"
    JWT_SECRET_KEY = "chenhaohau"
    
    # 关闭SQLAlchemy的修改跟踪，节省性能
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 获取用户账号密码和实例信息
    MYSQL_USER = "chenhaohua"
    MYSQL_PASSWORD = "GxMzks1bsTLwZWmL"
    MYSQL_HOST = "mysql2.sqlpub.com"
    MYSQL_PORT = "3307"
    MYSQL_NAME = "chhgraduationdesign"

    # 基本校验：避免运行时无效连接信息


    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_NAME}?charset=utf8mb4"
    )

    # DeepSeek 配置（集中管理，不依赖 .env）
    DEEPSEEK_API_KEY = "sk-7e7ee707daf0430b9ed805e2672090ec"
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    DEEPSEEK_MODEL = "deepseek-chat"
    DEEPSEEK_TIMEOUT = 300
    LLM_ENABLED = True
    LLM_DEBUG = False


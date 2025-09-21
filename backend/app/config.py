import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()


class Config:
    # 简化：直接从.env读取，不提供默认值
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    
    # 关闭SQLAlchemy的修改跟踪，节省性能
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Prometheus用于数据库性能监控、指标采集
    PROMETHEUS_BASE_URL = os.getenv("PROMETHEUS_BASE_URL", "http://192.168.112.128:9090")

    # MySQL数据库配置 - 直接从.env读取
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_NAME = os.getenv("MYSQL_NAME")

    # 简化验证：只检查是否存在
    if not all([MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_NAME]):
        raise RuntimeError("请检查 .env 文件中的 MySQL 配置")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_NAME}?charset=utf8mb4"
    )

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "300"))
    LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
    LLM_DEBUG = os.getenv("LLM_DEBUG", "false").lower() == "true"
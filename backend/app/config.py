import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Prometheus configuration
    PROMETHEUS_BASE_URL = os.getenv("PROMETHEUS_BASE_URL", "http://192.168.112.128:9090")

    # 默认 SQLite；DB_TYPE 统一小写处理
    # 数据库类型（仍保留 DB_TYPE 切换；若你想强制 MySQL，也可把这个判断去掉）
    DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

    if DB_TYPE == "mysql":
        # 仅使用 MYSQL_* 环境变量，不再读取/兼容 DB_* 变量
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
        MYSQL_NAME = os.getenv("MYSQL_NAME") or os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB")

        if not all([MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_NAME]):
            raise RuntimeError(
                "缺少必须的 MYSQL_* 环境变量，请设置：MYSQL_HOST、MYSQL_PORT(可选，默认3306)、MYSQL_USER、MYSQL_PASSWORD、MYSQL_NAME"
            )

        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_NAME}?charset=utf8mb4"
        )
    else:
        # SQLite URI (normalize path for Windows)
        _abs_path = os.path.abspath(SQLITE_DB)
        # 确保目录存在，避免 SQLite 无法创建数据库文件
        _dir = os.path.dirname(_abs_path)
        try:
            os.makedirs(_dir, exist_ok=True)
        except Exception:
            pass
        if os.name == 'nt':
            _abs_path = _abs_path.replace('\\', '/')
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_abs_path}"

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    
    # DeepSeek API configuration
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))
    LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
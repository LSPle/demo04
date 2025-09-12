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
    DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
    SQLITE_DB = os.getenv("SQLITE_DB", os.path.join(os.path.dirname(__file__), "..", "data", "app.db"))

    if DB_TYPE == "mysql":
        # 兼容两套变量名：优先读取 DB_*，否则退回 MYSQL_*
        def _env(*keys, default=None):
            for k in keys:
                v = os.getenv(k)
                if v is not None and v != "":
                    return v
            return default

        MYSQL_USER = _env("DB_USER", "MYSQL_USER", default="root")
        MYSQL_PASSWORD = _env("DB_PASSWORD", "MYSQL_PASSWORD", default="")
        MYSQL_HOST = _env("DB_HOST", "MYSQL_HOST", default="localhost")
        MYSQL_PORT = _env("DB_PORT", "MYSQL_PORT", default="3306")
        MYSQL_DB = _env("DB_NAME", "MYSQL_DB", default="flask_app")

        # 对用户名/密码做 URL 编码，避免特殊字符破坏连接串
        _user_enc = quote_plus(MYSQL_USER or "")
        _pwd_enc = quote_plus(MYSQL_PASSWORD or "")

        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{_user_enc}:{_pwd_enc}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
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
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "30"))
    LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
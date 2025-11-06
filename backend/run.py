import os
import logging
from app import create_app

# 先创建应用对象
app = create_app()

if __name__ == "__main__":
    # 还原为从环境变量读取，默认5000
    port = int(os.getenv("PORT", 5000))
    # 禁用调试模式与自动重载，避免重复监听导致请求被中止
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

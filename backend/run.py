import os
import logging
from app import create_app

# 创建 Flask 应用实例
# create_app 是工厂函数，负责创建和配置 Flask 应用对象
app = create_app()

if __name__ == "__main__":
    # 仅当直接运行此脚本时执行（而非被导入时）
    import sys
    
    # 设置标准输出和错误输出的编码为 UTF-8
    # 解决在 Windows 控制台可能出现的中文乱码问题
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    # 获取运行端口，优先从环境变量 PORT 获取，默认为 5000
    port = int(os.getenv("PORT", 5000))
    
    # 启动应用服务器
    # host="0.0.0.0": 监听所有网络接口，允许局域网访问
    # debug=False: 关闭调试模式
    # use_reloader=False: 关闭代码修改自动重启
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

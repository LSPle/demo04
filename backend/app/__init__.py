from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# 跨域支持，允许所有来源访问
# pip install flask-cors

from flask_cors import CORS
# 提供JWT的能力
from flask_jwt_extended import JWTManager

from .config import Config

# 初始化扩展

db = SQLAlchemy()
#提供JWT的能力
jwt = JWTManager()



def create_app():
    #  创建 Flask 应用实例的核心代码。
    app = Flask(__name__)

    #  Flask 框架中加载配置的常用方法
    app.config.from_object(Config)

    #应用初始化拓展
    db.init_app(app)
    jwt.init_app(app)
    # r 防止 / 被转译
    # 所有以 /api/ 开头的网址都允许跨域访问
    # origins 指的是“来源”，即“请求是从哪个网站发过来的”
    # "*" 代表 “所有来源” 或 “任何网站”
    CORS(app, resources={r"/api/*": {"origins": "*"}})


    #导入蓝图对象
    from .routes.auth import auth_bp
    from .routes.instances import instances_bp
    from .routes.config_optimize import config_optimize_bp
    from .routes.sql_analyze import sql_analyze_bp

    from .routes.slowlog import slowlog_bp
    from .routes.monitor import monitor_bp
    
    from .routes.arch_optimize import arch_opt_bp

    # 注册蓝图对象
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(instances_bp, url_prefix='/api')
    app.register_blueprint(config_optimize_bp, url_prefix='/api')
    app.register_blueprint(sql_analyze_bp, url_prefix='/api')

    app.register_blueprint(slowlog_bp, url_prefix='/api')
    app.register_blueprint(monitor_bp, url_prefix='/api')

    app.register_blueprint(arch_opt_bp, url_prefix='/api')
    # 根据models.py的模型初始化数据库
    # db.create_all() 是 Flask-SQLAlchemy 库自带的一个方法
    with app.app_context():
        db.create_all()
    
    # 注入app到监控服务，避免后台线程的上下文错误（保留手动检测服务的上下文支持）打算删除
    from .services.instance_monitor_service import instance_monitor_service
    instance_monitor_service.set_app(app)
    

    
    # 统一日志配置
    import logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


    return app



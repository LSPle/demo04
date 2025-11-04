import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import Config

# 初始化扩展

db = SQLAlchemy()
#提供JWT的能力
jwt = JWTManager()



def create_app():
    app = Flask(__name__)

    #加载配置
    app.config.from_object(Config)

    #应用初始化拓展
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})


    #导入功能
    from .routes.auth import auth_bp
    from .routes.instances import instances_bp
    from .routes.config_optimize import config_optimize_bp
    from .routes.sql_analyze import sql_analyze_bp

    from .routes.slowlog import slowlog_bp
    from .routes.monitor import monitor_bp
    
    from .routes.arch_optimize import arch_opt_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(instances_bp, url_prefix='/api')
    app.register_blueprint(config_optimize_bp, url_prefix='/api')
    app.register_blueprint(sql_analyze_bp, url_prefix='/api')

    app.register_blueprint(slowlog_bp, url_prefix='/api')
    app.register_blueprint(monitor_bp, url_prefix='/api')

    app.register_blueprint(arch_opt_bp, url_prefix='/api')

    # Serve React build files
    build_dir = os.path.join(os.path.dirname(os.path.dirname(app.root_path)), 'build')
    # Point Flask default static route to React build dir so /static/* works
    app.static_folder = os.path.join(build_dir, 'static')
    app.static_url_path = '/static'

    @app.route('/')
    def serve_react_app():
        return send_from_directory(build_dir, 'index.html')

    @app.route('/<path:filename>')
    def serve_static_files(filename):
        full_path = os.path.join(build_dir, filename)
        if os.path.exists(full_path):
            return send_from_directory(build_dir, filename)
        #返回html让react自己处理
        return send_from_directory(build_dir, 'index.html')

    # 根据models.py的模型初始化数据库
    with app.app_context():
        db.create_all()
    
    # 注入app到监控服务，避免后台线程的上下文错误（保留手动检测服务的上下文支持）
    from .services.instance_monitor_service import instance_monitor_service
    instance_monitor_service.set_app(app)
    

    
    return app

    # 暂时保留

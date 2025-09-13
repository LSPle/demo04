from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from .. import db
from ..models import UserInfo

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
def register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'message': 'username and password are required'}), 400

    # userinfo: 主键为 userId(varchar)
    if UserInfo.query.filter_by(user_id=username).first():
        return jsonify({'message': 'username already exists'}), 400

    user = UserInfo(user_id=username, password=password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'registered successfully', 'user': user.to_public()}), 201


# 函数：login()
@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'message': 'username and password are required'}), 400

    user = UserInfo.query.filter_by(user_id=username).first()
    if not user or (user.password or '') != password:
        return jsonify({'message': 'invalid credentials'}), 401

    # 这里的 identity 以 userId(varchar) 作为载荷
    access_token = create_access_token(identity=user.user_id)
    # 登录成功：增加活跃会话数，并按需启动监控线程（延迟导入避免循环依赖）
    try:
        from ..services.websocket_service import websocket_service
        websocket_service.increment_active_sessions()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"登录后启动监控失败: {e}")
    return jsonify({'access_token': access_token, 'user': user.to_public()}), 200


# 新增函数：logout()
@auth_bp.post('/logout')
def logout():
    """前端在用户退出时调用，用于减少活跃会话并在必要时停止监控线程"""
    try:
        from ..services.websocket_service import websocket_service
        websocket_service.decrement_active_sessions()
        return jsonify({'message': 'logged out'}), 200
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"退出登录停止监控失败: {e}")
        return jsonify({'message': 'logout error'}), 200


@auth_bp.get('/me')
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = UserInfo.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'message': 'user not found'}), 404
    return jsonify({'user': user.to_public()}), 200
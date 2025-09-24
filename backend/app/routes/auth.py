from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from .. import db
from ..models import UserInfo

'''
    用户认证

'''
auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    # 检查用户名和密码是否为空
    if not username or not password:
        return jsonify({'message': 'username and password are required'}), 400
    
    # 去除空格
    username = username.strip()
    password = password.strip()
    
    # 检查用户是否已存在
    existing_user = UserInfo.query.filter_by(user_id=username).first()
    if existing_user:
        return jsonify({'message': 'username already exists'}), 400

    # 创建新用户
    new_user = UserInfo(user_id=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'registered successfully', 'user': new_user.to_public()}), 201


@auth_bp.post('/login')
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')

    # 检查用户名和密码是否为空
    if not username or not password:
        return jsonify({'message': 'username and password are required'}), 400
    
    # 去除空格
    username = username.strip()
    password = password.strip()

    # 查找用户
    user = UserInfo.query.filter_by(user_id=username).first()
    if not user:
        return jsonify({'message': 'invalid credentials'}), 401
    
    # 验证密码
    if user.password != password:
        return jsonify({'message': 'invalid credentials'}), 401

    # 生成token
    access_token = create_access_token(identity=user.user_id)
    
    # 登录成功后启动监控
    try:
        from ..services.websocket_service import websocket_service
        websocket_service.increment_active_sessions()
    except:
        pass  # 如果启动失败就忽略
    
    return jsonify({'access_token': access_token, 'user': user.to_public()}), 200


@auth_bp.post('/logout')
def logout():
    # 退出登录时停止监控
    try:
        from ..services.websocket_service import websocket_service
        websocket_service.decrement_active_sessions()
    except:
        pass  # 如果停止失败就忽略
    
    return jsonify({'message': 'logged out'}), 200


@auth_bp.get('/me')
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = UserInfo.query.filter_by(user_id=user_id).first()
    
    if not user:
        return jsonify({'message': 'user not found'}), 404
    
    return jsonify({'user': user.to_public()}), 200
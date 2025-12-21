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
        return jsonify({'message': '信息不能为空'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    # 检查用户名和密码是否为空
    if not username or not password:
        return jsonify({'message': '账号密码不能为空'}), 400
    
    # 去除空格
    username = username.strip()
    password = password.strip()
    
    # 检查用户是否已存在
    existing_user = UserInfo.query.filter_by(user_id=username).first()
    if existing_user:
        return jsonify({'message': '用户已经存在'}), 400

    # 创建新用户
    new_user = UserInfo(user_id=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': "注册成功", 'user': new_user.to_public()}), 201


@auth_bp.post('/login')
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': '信息不能为空'}), 400
    
    username = data.get('username')
    password = data.get('password')

    # 检查用户名和密码是否为空
    if not username or not password:
        return jsonify({'message': '账号密码不能为空'}), 400
    
    # 去除空格
    username = username.strip()
    password = password.strip()

    # 查找用户
    user = UserInfo.query.filter_by(user_id=username).first()
    if not user:
        return jsonify({'message': '用户不存在'}), 401
    
    # 验证密码
    if user.password != password:
        return jsonify({'message': '账号密码错误'}), 401

    # 生成token，flask_jwt_extended扩展
    access_token = create_access_token(identity=user.user_id)
    

    
    return jsonify({'access_token': access_token, 'user': user.to_public()}), 200


@auth_bp.post('/logout')
def logout():

    
    return jsonify({'message': '登出成功'}), 200


@auth_bp.get('/me')
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = UserInfo.query.filter_by(user_id=user_id).first()
    
    if not user:
        return jsonify({'message': '用户不存在'}), 404
    
    return jsonify({'user': user.to_public()}), 200
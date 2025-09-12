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
    return jsonify({'access_token': access_token, 'user': user.to_public()}), 200


@auth_bp.get('/me')
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = UserInfo.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'message': 'user not found'}), 404
    return jsonify({'user': user.to_public()}), 200
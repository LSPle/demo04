from functools import wraps
from flask import request, jsonify
from ..models import User

def token_required(f):
    """简单token认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'token required'}), 401
        
        # 移除 'Bearer ' 前缀（如果存在）
        if token.startswith('Bearer '):
            token = token[7:]
        
        user = User.verify_token(token)
        if not user:
            return jsonify({'error': 'invalid token'}), 401
        
        # 将用户信息传递给被装饰的函数
        return f(user, *args, **kwargs)
    
    return decorated_function
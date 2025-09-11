import logging
from functools import wraps
from flask import jsonify
from typing import Callable, Any, Tuple, Optional

logger = logging.getLogger(__name__)


def handle_api_errors(default_error_message: str = "操作失败", 
                     log_errors: bool = True,
                     return_tuple: bool = False):
    """API错误处理装饰器
    
    Args:
        default_error_message: 默认错误消息
        log_errors: 是否记录错误日志
        return_tuple: 是否返回元组格式 (success, data, message)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except ValueError as e:
                error_msg = f"数据格式错误: {str(e)}"
                if log_errors:
                    logger.warning(f"{func.__name__}: {error_msg}")
                
                if return_tuple:
                    return False, None, error_msg
                return jsonify({'error': error_msg}), 400
                
            except Exception as e:
                error_msg = f"{default_error_message}: {str(e)}"
                if log_errors:
                    logger.error(f"{func.__name__}: {error_msg}")
                
                if return_tuple:
                    return False, None, error_msg
                return jsonify({'error': error_msg}), 500
                
        return wrapper
    return decorator


def handle_database_errors(operation_name: str = "数据库操作"):
    """数据库操作错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                from .. import db
                db.session.rollback()
                error_msg = f"{operation_name}失败: {str(e)}"
                logger.error(f"{func.__name__}: {error_msg}")
                return False, None, error_msg
        return wrapper
    return decorator


def safe_execute(func: Callable, default_return: Any = None, 
                log_prefix: str = "") -> Tuple[bool, Any, str]:
    """安全执行函数，统一错误处理
    
    Args:
        func: 要执行的函数
        default_return: 失败时的默认返回值
        log_prefix: 日志前缀
    
    Returns:
        (success, result, error_message)
    """
    try:
        result = func()
        return True, result, ""
    except Exception as e:
        error_msg = str(e)
        if log_prefix:
            logger.error(f"{log_prefix}: {error_msg}")
        else:
            logger.error(f"执行失败: {error_msg}")
        return False, default_return, error_msg


class ErrorResponse:
    """统一错误响应格式"""
    
    @staticmethod
    def bad_request(message: str):
        return jsonify({'error': message}), 400
    
    @staticmethod
    def not_found(message: str = "资源不存在"):
        return jsonify({'error': message}), 404
    
    @staticmethod
    def internal_error(message: str = "服务器内部错误"):
        return jsonify({'error': message}), 500
    
    @staticmethod
    def validation_error(message: str):
        return jsonify({'error': f"验证失败: {message}"}), 400
    
    @staticmethod
    def connection_error(message: str):
        return jsonify({'error': f"连接失败: {message}"}), 400
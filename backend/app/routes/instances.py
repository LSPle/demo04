from flask import Blueprint, jsonify, request
from ..models import db, Instance
from ..utils.db_connection import db_connection_manager
from ..services.table_analyzer_service import table_analyzer_service
import pymysql
from datetime import datetime

'''
    实例管理
'''

#获取实例、创建新实例、更新实例、删除实例、获取单个实例
#获取数据库列表、获取表列表、获取表结构

instances_bp = Blueprint('instances', __name__)

# 获取用户的实例查询对象
def get_user_instances_query(user_id):
    query = Instance.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query

# 验证实例数据( is_update 用于区分实例更新还是创建实例)
def validate_instance_data(data, is_update=False):
    
    # 统一清洗：去除常见字段的前后空格
    for key in ['name', 'host', 'type', 'username', 'password']:
        if key in data and isinstance(data[key], str):
            data[key] = data[key].strip()
    
    # 检查必需字段（仅在创建时）
    if not is_update:
        required_fields = ['name', 'host', 'port', 'type']
        for field in required_fields:
            if field not in data or not data[field]:
                return False, f'缺少必需字段: {field}'
    
    # 简单验证：检查字段是否为空
    if 'name' in data and not data['name']:
        return False, '实例名称不能为空'
    
    if 'host' in data and not data['host']:
        return False, '主机地址不能为空'
    
    if 'port' in data:
        port = int(data['port'])
        if port <= 0:
            return False, '端口号必须大于0'
    
    return True, '验证通过'

# 获取实例列表
@instances_bp.get('/instances')
def list_instances():
    # args只读字典，获取用户ID
    user_id = request.args.get('userId')
    # 获取实例
    instances = get_user_instances_query(user_id).all()
    result = []
    for instance in instances:
        result.append(instance.to_dict())
    return jsonify(result), 200

"""创建新实例"""
@instances_bp.post('/instances')
def create_instance():
 
    try:
        data = request.get_json()
        # 基础清洗：去除用户名/密码/主机/名称的空格
        for key in ['username', 'password', 'host', 'name', 'type']:
            if key in data and isinstance(data[key], str):
                data[key] = data[key].strip()
        
        user_id = request.args.get('userId')
        
        # 验证数据
        is_valid, error_msg = validate_instance_data(data)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # 验证数据库连接
        is_ok, msg = db_connection_manager.validate_connection(
            db_type=data['type'],
            host=data['host'],
            port=int(data['port']),
            username=data.get('username', ''),
            password=data.get('password', '')
        )
        if not is_ok:
            return jsonify({'error': f'连接校验失败：{msg}'}), 400
        
        # 创建实例
        instance = Instance(
            instance_name=data['name'],
            host=data['host'],
            port=int(data['port']),
            username=data.get('username', ''),
            password=data.get('password', ''),
            db_type=data['type'],
            user_id=user_id,
            add_time=datetime.utcnow()
        )
        
        db.session.add(instance)
        db.session.commit()
        
        return jsonify({
            'message': '实例创建成功',
            'instance': instance.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

# 更新实例信息
@instances_bp.put('/instances/<int:instance_id>')
def update_instance(instance_id):
  
    try:
        user_id = request.args.get('userId')
        data = request.get_json()
        # 基础清洗：去除用户名/密码/主机/名称的空格
        for key in ['username', 'password', 'host', 'name', 'type']:
            if key in data and isinstance(data[key], str):
                data[key] = data[key].strip()
        
        # 查找实例
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        
        # 验证数据
        is_valid, error_msg = validate_instance_data(data, is_update=True)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # 如果更新了连接信息，验证连接
        connection_fields = ['host', 'port', 'username', 'password', 'type']
        if any(field in data for field in connection_fields):
            is_ok, msg = db_connection_manager.validate_connection(
                db_type=data.get('type', instance.db_type),
                host=data.get('host', instance.host),
                port=int(data.get('port', instance.port)),
                username=data.get('username', instance.username or ''),
                password=data.get('password', instance.password or '')
            )
            if not is_ok:
                return jsonify({'error': f'连接校验失败：{msg}'}), 400
        
        # 更新实例信息（不再接受/写入status字段）
        if 'name' in data:
            instance.instance_name = data['name']
        if 'host' in data:
            instance.host = data['host']
        if 'port' in data:
            instance.port = int(data['port'])
        if 'username' in data:
            instance.username = data['username']
        if 'password' in data:
            instance.password = data['password']
        if 'type' in data:
            instance.db_type = data['type']
        # 显式忽略任何传入的 status
        if 'status' in data:
            pass
        # 新增、删除、修改需要使用提交
        db.session.commit()
        
        return jsonify({
            'message': '实例更新成功',
            'instance': instance.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

# 删除实例
@instances_bp.delete('/instances/<int:instance_id>')
def delete_instance(instance_id):
    
    try:
        user_id = request.args.get('userId')
        
        # 查找实例
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        
        instance_name = instance.instance_name
        db.session.delete(instance)
        db.session.commit()
        
        return jsonify({
            'message': f'实例 "{instance_name}" 删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


# 获取单个实例信息(获取版本号)
@instances_bp.get('/instances/<int:instance_id>')
def get_instance(instance_id):
    try:
        user_id = request.args.get('userId')
        
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        # 基础信息
        data = instance.to_dict()

        # 尝试获取数据库版本号（MySQL）
        ok, rows, err = db_connection_manager.execute_query(instance, "SELECT VERSION()")
        if ok and rows:
            data['version'] = str(rows[0][0])
        else:
            data['version'] = data.get('version') or None

        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

# 获取实例的数据库列表
@instances_bp.get('/instances/<int:instance_id>/databases')
def list_instance_databases(instance_id):
    try:
        user_id = request.args.get('userId')
        
        # 查找实例
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        
        # 使用统一的连接管理器执行查询，获取数据库列表
        ok, rows, err = db_connection_manager.execute_query(instance, "SHOW DATABASES")
        # 为保持之前的容错行为：若失败，返回空列表但状态仍为200
        if not ok:
            return jsonify({'error': err}), 500

        # 提取数据库名称（MySQL默认返回序列结构）
        databases = []
        for row in rows:
            if row:
                databases.append(row[0])

        databases.sort()
        return jsonify({'databases': databases}), 200
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

# 获取数据库的表列表
@instances_bp.get('/instances/<int:instance_id>/databases/<string:database>/tables')
def list_tables(instance_id, database):
    try:
        user_id = request.args.get('userId')
        
        # 查找实例
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        
        # 使用统一的连接管理器执行查询，获取表列表
        ok, rows, err = db_connection_manager.execute_query(instance, "SHOW TABLES", database=database)
        if not ok:
            return jsonify({'error': err}), 500

        # 提取表名（MySQL默认返回序列结构）
        tables = []
        for row in rows:
            if row:
                tables.append(row[0])

        tables.sort()
        return jsonify({'tables': tables}), 200
            
    except Exception as e:
        return jsonify({'error': f'获取数据表失败: {str(e)}'}), 500


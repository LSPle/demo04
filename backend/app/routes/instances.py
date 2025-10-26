from flask import Blueprint, jsonify, request
from ..models import db, Instance
from ..utils.db_connection import db_connection_manager
from ..services.database_service import database_service
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
    """根据用户ID获取实例查询对象"""
    query = Instance.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query

# 验证实例数据
def validate_instance_data(data, is_update=False):
    """验证实例数据的有效性"""
    if not data:
        return False, '请求体不能为空'
    
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
    
    # 验证实例名称
    if 'name' in data:
        if not isinstance(data['name'], str) or len(data['name'].strip()) == 0:
            return False, '实例名称必须是非空字符串'
    
    # 验证主机地址
    if 'host' in data:
        if not isinstance(data['host'], str) or len(data['host'].strip()) == 0:
            return False, '主机地址必须是非空字符串'
    
    # 验证端口号
    if 'port' in data:
        try:
            port = int(data['port'])
            if port < 1 or port > 65535:
                return False, '端口号必须在1-65535范围内'
        except (ValueError, TypeError):
            return False, '端口号必须是有效的整数'
    
    # 验证数据库类型
    if 'type' in data:
        if data['type'] not in ['MySQL']:
            return False, '不支持的数据库类型'
    
    return True, '验证通过'

"""获取实例列表"""
@instances_bp.get('/instances')
def list_instances():
    
    user_id = request.args.get('userId')
    #获取实例
    instances = get_user_instances_query(user_id).all()
    # return jsonify([i.to_dict() for i in instances]), 200
    instances_dicts = []
    for instance in instances:
        instances_dicts.append(instance.to_dict())
    return jsonify(instances_dicts), 200

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

"""更新实例信息"""
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
        
        db.session.commit()
        
        return jsonify({
            'message': '实例更新成功',
            'instance': instance.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

"""删除实例"""
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

@instances_bp.get('/instances/<int:instance_id>')
def get_instance(instance_id):
    """获取单个实例信息"""
    try:
        user_id = request.args.get('userId')
        
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        # 基础信息
        data = instance.to_dict()

        # 尝试获取数据库版本号（MySQL）
        try:
            conn = pymysql.connect(
                host=instance.host,
                port=int(instance.port or 3306),
                user=instance.username or '',
                password=instance.password or '',
                database='mysql',
                charset='utf8mb4',
                connect_timeout=2,
                read_timeout=2,
                write_timeout=2,
                cursorclass=pymysql.cursors.Cursor
            )
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT VERSION()')
                    row = cur.fetchone()
                    if row:
                        data['version'] = str(row[0])
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception:
            # 无法连接或无权限时不抛错，版本号置为未知
            data['version'] = data.get('version') or None

        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

"""获取实例的数据库列表"""
@instances_bp.get('/instances/<int:instance_id>/databases')
def list_instance_databases(instance_id):
    
    try:
        user_id = request.args.get('userId')
        
        # 查找实例
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        
        # 获取数据库列表
        ok, databases, msg = database_service.list_databases(instance)
        if not ok:
            status_code = 400 if msg in ['仅支持MySQL实例'] else 500
            return jsonify({'error': msg}), status_code
        
        return jsonify({'databases': databases}), 200
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

"""获取数据库的表列表"""
@instances_bp.get('/instances/<int:instance_id>/databases/<string:database>/tables')
def list_tables(instance_id, database):
    
    try:
        user_id = request.args.get('userId')
        
        # 查找实例
        instance = get_user_instances_query(user_id).filter_by(id=instance_id).first()
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        
        # 检查数据库类型
        if instance.db_type != 'MySQL':
            return jsonify({'error': '仅支持MySQL实例'}), 400
        
        if not pymysql:
            return jsonify({'error': 'MySQL驱动不可用'}), 500

        # 连接数据库获取表列表
        conn = pymysql.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username or '',
            password=instance.password or '',
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                rows = cursor.fetchall()
                
                # 提取表名
                tables = []
                for row in rows:
                    if isinstance(row, dict) and row:
                        tables.append(list(row.values())[0])
                    elif isinstance(row, (list, tuple)) and row:
                        tables.append(row[0])
                
                tables.sort()
            
            return jsonify({'tables': tables}), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': f'获取数据表失败: {str(e)}'}), 500

"""获取数据库的表结构"""

@instances_bp.get('/instances/<int:instance_id>/databases/<string:database>/tables/<string:table_name>/schema')
def get_table_schema(instance_id, database, table_name):
    
    try:
        # 查找实例
        instance = Instance.query.get(instance_id)
        if not instance:
            return jsonify({'error': '实例不存在'}), 404
        
        # 检查数据库类型
        if instance.db_type != 'MySQL':
            return jsonify({'error': '仅支持MySQL实例'}), 400

        # 获取表结构
        ok, schema, msg = table_analyzer_service._get_table_metadata_only(instance, database, table_name)
        if not ok:
            return jsonify({'error': msg}), 400
        
        return jsonify({'schema': schema}), 200
        
    except Exception as e:
        return jsonify({'error': f'获取表结构失败: {str(e)}'}), 500
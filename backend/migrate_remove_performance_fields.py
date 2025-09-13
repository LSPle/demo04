#!/usr/bin/env python3
"""
数据库迁移脚本：移除实例表中的性能指标字段

此脚本用于清理instances表中已删除的性能指标字段：
- cpu_usage
- memory_usage  
- storage

运行方式：
python migrate_remove_performance_fields.py
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import Config

def migrate_sqlite():
    """迁移SQLite数据库"""
    config = Config()
    
    # 解析SQLite数据库路径
    db_uri = config.SQLALCHEMY_DATABASE_URI
    if not db_uri.startswith('sqlite:///'):
        print("错误：当前配置不是SQLite数据库")
        return False
        
    db_path = db_uri.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在：{db_path}")
        print("无需迁移，字段已不存在")
        return True
        
    print(f"开始迁移SQLite数据库：{db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instances'")
        if not cursor.fetchone():
            print("instances表不存在，无需迁移")
            return True
            
        # 获取当前表结构
        cursor.execute("PRAGMA table_info(instances)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # 检查需要删除的字段是否存在
        fields_to_remove = ['cpu_usage', 'memory_usage', 'storage']
        existing_fields = [field for field in fields_to_remove if field in column_names]
        
        if not existing_fields:
            print("需要删除的字段不存在，无需迁移")
            return True
            
        print(f"发现需要删除的字段：{existing_fields}")
        
        # 保留的字段列表
        keep_columns = [col for col in column_names if col not in fields_to_remove]
        keep_columns_str = ', '.join(keep_columns)
        
        print(f"保留的字段：{keep_columns}")
        
        # SQLite不支持直接删除列，需要重建表
        # 0. 清理可能存在的临时表
        cursor.execute("DROP TABLE IF EXISTS instances_new")
        
        # 1. 创建新表（包含所有保留的字段）
        cursor.execute("""
            CREATE TABLE instances_new (
                id INTEGER PRIMARY KEY,
                instance_name VARCHAR(128) NOT NULL,
                host VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL DEFAULT 3306,
                username VARCHAR(128),
                password VARCHAR(255),
                db_type VARCHAR(64) NOT NULL DEFAULT 'MySQL',
                version VARCHAR(64),
                status VARCHAR(32) NOT NULL DEFAULT 'running',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. 复制数据
        cursor.execute(f"""
            INSERT INTO instances_new ({keep_columns_str})
            SELECT {keep_columns_str} FROM instances
        """)
        
        # 3. 删除旧表
        cursor.execute("DROP TABLE instances")
        
        # 4. 重命名新表
        cursor.execute("ALTER TABLE instances_new RENAME TO instances")
        
        conn.commit()
        print("SQLite数据库迁移完成")
        return True
        
    except Exception as e:
        print(f"迁移失败：{e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def migrate_mysql():
    """迁移MySQL数据库"""
    try:
        import pymysql
    except ImportError:
        print("错误：PyMySQL未安装，无法连接MySQL")
        return False
        
    config = Config()
    
    # 解析MySQL连接信息
    db_uri = config.SQLALCHEMY_DATABASE_URI
    if not db_uri.startswith('mysql+pymysql://'):
        print("错误：当前配置不是MySQL数据库")
        return False
        
    print("开始迁移MySQL数据库")
    
    try:
        # 从配置获取连接参数
        conn = pymysql.connect(
            host=config.import os
from dotenv import load_dotenv
// ... existing code ...
from urllib.parse import quote_plus
// ... existing code ...,
            port=int(config.MYSQL_PORT),
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB,
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SHOW TABLES LIKE 'instances'")
        if not cursor.fetchone():
            print("instances表不存在，无需迁移")
            return True
            
        # 检查字段是否存在并删除
        fields_to_remove = ['cpu_usage', 'memory_usage', 'storage']
        
        for field in fields_to_remove:
            cursor.execute(f"SHOW COLUMNS FROM instances LIKE '{field}'")
            if cursor.fetchone():
                print(f"删除字段：{field}")
                cursor.execute(f"ALTER TABLE instances DROP COLUMN {field}")
            else:
                print(f"字段 {field} 不存在，跳过")
                
        conn.commit()
        print("MySQL数据库迁移完成")
        return True
        
    except Exception as e:
        print(f"迁移失败：{e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """主函数"""
    print("=== 数据库迁移：移除性能指标字段 ===")
    
    config = Config()
    db_uri = config.SQLALCHEMY_DATABASE_URI
    
    print(f"数据库URI：{db_uri}")
    
    if db_uri.startswith('sqlite:///'):
        success = migrate_sqlite()
    elif db_uri.startswith('mysql+pymysql://'):
        success = migrate_mysql()
    else:
        print(f"不支持的数据库类型：{db_uri}")
        success = False
        
    if success:
        print("\n✅ 迁移成功完成")
        print("已移除的字段：cpu_usage, memory_usage, storage")
        print("数据库结构已更新，与代码模型保持一致")
    else:
        print("\n❌ 迁移失败")
        print("请检查错误信息并手动处理")
        
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
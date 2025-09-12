#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为instances表添加user_id字段
"""

import sqlite3
import os
from app import create_app
from app.models import db

def migrate_database():
    """为instances表添加user_id字段"""
    app = create_app()
    
    with app.app_context():
        # 获取数据库文件路径
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        print(f"数据库路径: {db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 检查user_id列是否已存在
            cursor.execute("PRAGMA table_info(instances)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'user_id' not in columns:
                print("添加user_id列到instances表...")
                cursor.execute("ALTER TABLE instances ADD COLUMN user_id INTEGER")
                
                # 为现有实例设置默认user_id（如果有用户的话）
                cursor.execute("SELECT id FROM users LIMIT 1")
                user_result = cursor.fetchone()
                
                if user_result:
                    default_user_id = user_result[0]
                    cursor.execute("UPDATE instances SET user_id = ? WHERE user_id IS NULL", (default_user_id,))
                    print(f"为现有实例设置默认user_id: {default_user_id}")
                
                conn.commit()
                print("user_id列添加成功！")
            else:
                print("user_id列已存在，无需添加。")
                
            # 检查token列是否已存在
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [column[1] for column in cursor.fetchall()]
            
            if 'token' not in user_columns:
                print("添加token列到users表...")
                cursor.execute("ALTER TABLE users ADD COLUMN token TEXT")
                conn.commit()
                print("token列添加成功！")
            else:
                print("token列已存在，无需添加。")
                
        except Exception as e:
            print(f"迁移失败: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == '__main__':
    migrate_database()
    print("数据库迁移完成！")
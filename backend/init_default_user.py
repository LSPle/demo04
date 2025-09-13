#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化默认用户脚本
"""

import argparse

from app import create_app, db
from app.models import UserInfo


def init_default_user():
    """创建默认用户 admin/admin123"""
    app = create_app()
    
    with app.app_context():
        # 检查是否已存在admin用户（userinfo表）
        existing_info = UserInfo.query.filter_by(user_id='admin').first()
        if existing_info:
            print("默认用户 'admin' 已存在 (userinfo 表)")
        else:
            admin_info = UserInfo(user_id='admin', password='admin123')
            db.session.add(admin_info)
            db.session.commit()
            print("已在 userinfo 表创建默认用户: admin/admin123")


def delete_admin_user():
    """删除默认用户 admin（从 userinfo 表中删除记录）"""
    app = create_app()

    with app.app_context():
        # 删除 userinfo 表中的 admin
        info = UserInfo.query.filter_by(user_id='admin').first()
        if info:
            db.session.delete(info)
            db.session.commit()
            print("已从 userinfo 表删除 'admin'")
        else:
            print("userinfo 表中未找到 'admin'")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='初始化/删除默认用户 admin')
    parser.add_argument('--delete', action='store_true', help='删除默认用户 admin（userinfo）')
    parser.add_argument('--create', action='store_true', help='创建默认用户 admin/admin123（userinfo）')
    args = parser.parse_args()

    if args.delete:
        delete_admin_user()
    else:
        # 默认行为：创建（兼容历史用法）；若显式传入 --create 也执行创建
        init_default_user()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ubuntu实例状态测试脚本
专门测试Ubuntu 192.168.112.128:3306实例的状态变化
"""

import requests
import time
import json
from app.models import Instance
from app import create_app, db
from app.services.instance_monitor_service import instance_monitor_service

def test_ubuntu_instance():
    """测试Ubuntu实例状态"""
    app = create_app()
    
    with app.app_context():
        # 查找Ubuntu实例
        ubuntu_instance = Instance.query.filter_by(
            host='192.168.112.128',
            port=3306
        ).first()
        
        if not ubuntu_instance:
            print("未找到Ubuntu实例 (192.168.112.128:3306)")
            return
            
        print(f"找到Ubuntu实例: {ubuntu_instance.instance_name}")
        print(f"当前状态: {ubuntu_instance.status}")
        print(f"主机: {ubuntu_instance.host}:{ubuntu_instance.port}")
        print("\n开始测试连接状态...")
        
        # 测试连接状态
        for i in range(5):
            print(f"\n=== 第 {i+1} 次检测 ===")
            
            # 检查连接状态
            is_connected, message = instance_monitor_service.check_instance_connection(ubuntu_instance)
            new_status = 'running' if is_connected else 'error'
            
            print(f"连接状态: {'成功' if is_connected else '失败'}")
            print(f"状态消息: {message}")
            print(f"新状态: {new_status}")
            
            # 更新数据库状态
            old_status = ubuntu_instance.status
            instance_monitor_service.update_instance_status(ubuntu_instance, is_connected, message)
            
            # 重新查询以获取最新状态
            db.session.refresh(ubuntu_instance)
            print(f"数据库状态: {old_status} -> {ubuntu_instance.status}")
            
            if old_status != ubuntu_instance.status:
                print("✅ 状态发生变化！")
            else:
                print("ℹ️  状态未变化")
                
            time.sleep(3)
            
        print("\n测试完成！")
        print(f"最终状态: {ubuntu_instance.status}")

if __name__ == '__main__':
    test_ubuntu_instance()
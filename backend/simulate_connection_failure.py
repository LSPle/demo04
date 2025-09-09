#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟连接失败测试脚本
通过临时修改实例配置来模拟连接失败，测试WebSocket实时更新
"""

import time
from app import create_app, db
from app.models import Instance
from app.services.instance_monitor_service import instance_monitor_service

def simulate_ubuntu_failure():
    """模拟Ubuntu实例连接失败"""
    app = create_app()
    
    with app.app_context():
        # 查找Ubuntu实例
        ubuntu_instance = Instance.query.filter_by(
            host='192.168.112.128',
            port=3306
        ).first()
        
        if not ubuntu_instance:
            print("未找到Ubuntu实例")
            return
            
        print(f"找到Ubuntu实例: {ubuntu_instance.instance_name}")
        print(f"当前状态: {ubuntu_instance.status}")
        
        # 保存原始配置
        original_port = ubuntu_instance.port
        original_password = ubuntu_instance.password
        
        try:
            print("\n=== 步骤1: 模拟端口不可达 ===")
            # 修改为不存在的端口
            ubuntu_instance.port = 9999
            db.session.commit()
            
            # 等待监控检测
            print("等待监控检测...")
            time.sleep(8)  # 等待超过监控间隔
            
            # 手动触发检测
            is_connected, message = instance_monitor_service.check_instance_connection(ubuntu_instance)
            print(f"连接状态: {'成功' if is_connected else '失败'}")
            print(f"状态消息: {message}")
            
            # 更新状态
            instance_monitor_service.update_instance_status(ubuntu_instance, is_connected, message)
            db.session.refresh(ubuntu_instance)
            print(f"数据库状态: {ubuntu_instance.status}")
            
            print("\n=== 步骤2: 恢复正常配置 ===")
            # 恢复原始端口
            ubuntu_instance.port = original_port
            db.session.commit()
            
            # 等待监控检测
            print("等待监控检测...")
            time.sleep(8)
            
            # 手动触发检测
            is_connected, message = instance_monitor_service.check_instance_connection(ubuntu_instance)
            print(f"连接状态: {'成功' if is_connected else '失败'}")
            print(f"状态消息: {message}")
            
            # 更新状态
            instance_monitor_service.update_instance_status(ubuntu_instance, is_connected, message)
            db.session.refresh(ubuntu_instance)
            print(f"数据库状态: {ubuntu_instance.status}")
            
            print("\n=== 步骤3: 模拟认证失败 ===")
            # 修改为错误密码
            ubuntu_instance.password = 'wrong_password'
            db.session.commit()
            
            # 等待监控检测
            print("等待监控检测...")
            time.sleep(8)
            
            # 手动触发检测
            is_connected, message = instance_monitor_service.check_instance_connection(ubuntu_instance)
            print(f"连接状态: {'成功' if is_connected else '失败'}")
            print(f"状态消息: {message}")
            
            # 更新状态
            instance_monitor_service.update_instance_status(ubuntu_instance, is_connected, message)
            db.session.refresh(ubuntu_instance)
            print(f"数据库状态: {ubuntu_instance.status}")
            
            print("\n=== 步骤4: 完全恢复 ===")
            # 恢复所有原始配置
            ubuntu_instance.password = original_password
            db.session.commit()
            
            # 等待监控检测
            print("等待监控检测...")
            time.sleep(8)
            
            # 手动触发检测
            is_connected, message = instance_monitor_service.check_instance_connection(ubuntu_instance)
            print(f"连接状态: {'成功' if is_connected else '失败'}")
            print(f"状态消息: {message}")
            
            # 更新状态
            instance_monitor_service.update_instance_status(ubuntu_instance, is_connected, message)
            db.session.refresh(ubuntu_instance)
            print(f"最终状态: {ubuntu_instance.status}")
            
        except Exception as e:
            print(f"测试过程中出错: {e}")
            # 确保恢复原始配置
            ubuntu_instance.port = original_port
            ubuntu_instance.password = original_password
            db.session.commit()
            
        print("\n测试完成！请检查前端页面是否显示了状态变化。")

if __name__ == '__main__':
    simulate_ubuntu_failure()
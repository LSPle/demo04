#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试WebSocket实时状态更新功能
模拟实例状态变化，验证前端是否能实时接收到更新
"""

import time
import pymysql
from app.models import Instance
from app import create_app, db
from app.services.instance_monitor_service import instance_monitor_service

def test_instance_status_change():
    """测试实例状态变化"""
    app = create_app()
    
    with app.app_context():
        # 获取所有实例
        instances = Instance.query.all()
        
        if not instances:
            print("没有找到实例，请先添加实例")
            return
            
        print(f"找到 {len(instances)} 个实例，开始测试状态变化...")
        
        for i in range(5):  # 测试5轮
            print(f"\n=== 第 {i+1} 轮测试 ===")
            
            for instance in instances:
                print(f"检测实例: {instance.instance_name} ({instance.host}:{instance.port})")
                
                # 检查实际连接状态
                try:
                    connection = pymysql.connect(
                        host=instance.host,
                        port=instance.port,
                        user=instance.username,
                        password=instance.password,
                        connect_timeout=5
                    )
                    connection.close()
                    is_connected = True
                    message = "连接正常"
                    print(f"  ✓ 连接成功")
                except Exception as e:
                    is_connected = False
                    message = f"连接失败: {str(e)}"
                    print(f"  ✗ 连接失败: {e}")
                
                # 更新实例状态
                old_status = instance.status
                instance_monitor_service.update_instance_status(instance, is_connected, message)
                new_status = instance.status
                
                if old_status != new_status:
                    print(f"  状态变化: {old_status} -> {new_status}")
                else:
                    print(f"  状态保持: {new_status}")
            
            print(f"等待 10 秒后进行下一轮测试...")
            time.sleep(10)
        
        print("\n测试完成！")

def simulate_instance_failure():
    """模拟实例故障"""
    app = create_app()
    
    with app.app_context():
        # 获取第一个实例
        instance = Instance.query.first()
        
        if not instance:
            print("没有找到实例")
            return
            
        print(f"模拟实例 {instance.instance_name} 故障...")
        
        # 模拟故障状态
        instance_monitor_service.update_instance_status(instance, False, "模拟故障：服务器无响应")
        print("已设置为故障状态")
        
        time.sleep(5)
        
        # 模拟恢复
        instance_monitor_service.update_instance_status(instance, True, "模拟恢复：服务器重新上线")
        print("已设置为正常状态")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "simulate":
        simulate_instance_failure()
    else:
        test_instance_status_change()
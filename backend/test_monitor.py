#!/usr/bin/env python3

from app import create_app
from app.services.instance_monitor_service import instance_monitor_service

def test_instance_monitor():
    """测试实例监控功能"""
    app = create_app()
    
    with app.app_context():
        print("开始检测实例状态...")
        total, normal, error = instance_monitor_service.check_all_instances()
        print(f"检测完成: 总数={total}, 正常={normal}, 异常={error}")
        
        print("\n获取状态汇总...")
        summary = instance_monitor_service.get_instance_status_summary()
        print(f"状态汇总: {summary}")

if __name__ == '__main__':
    test_instance_monitor()
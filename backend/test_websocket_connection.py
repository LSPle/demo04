#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket连接测试脚本
测试WebSocket服务是否正常工作
"""

import socketio
import time
import threading
from app import create_app
from app.services.websocket_service import websocket_service

def test_websocket_connection():
    """测试WebSocket连接"""
    print("开始测试WebSocket连接...")
    
    # 创建客户端
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✅ 客户端连接成功")
        
    @sio.event
    def disconnect():
        print("❌ 客户端断开连接")
        
    @sio.event
    def instance_status_change(data):
        print(f"📡 收到实例状态变化: {data}")
        
    @sio.event
    def status_summary_update(data):
        print(f"📊 收到状态汇总更新: {data}")
        
    @sio.event
    def instances_status_update(data):
        print(f"📋 收到所有实例状态更新: {len(data.get('instances', []))} 个实例")
    
    try:
        # 连接到服务器
        print("正在连接到 http://localhost:5001...")
        sio.connect('http://localhost:5001')
        
        # 检查监控线程状态
        print(f"监控线程状态: {websocket_service.monitoring_active}")
        print(f"监控线程存活: {websocket_service.monitoring_thread.is_alive() if websocket_service.monitoring_thread else False}")
        
        # 请求状态更新
        print("\n请求状态更新...")
        sio.emit('request_status_update')
        
        # 等待接收消息
        print("\n等待接收WebSocket消息（10秒）...")
        time.sleep(10)
        
        # 断开连接
        sio.disconnect()
        print("\n测试完成")
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        
def run_test_in_app_context():
    """在Flask应用上下文中运行测试"""
    app = create_app()
    with app.app_context():
        test_websocket_connection()

if __name__ == '__main__':
    # 在单独线程中运行测试，避免阻塞
    test_thread = threading.Thread(target=run_test_in_app_context)
    test_thread.start()
    test_thread.join()
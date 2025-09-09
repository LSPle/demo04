import { io } from 'socket.io-client';
import API_BASE_URL from '../config/api';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  /**
   * 连接到WebSocket服务器
   */
  connect() {
    if (this.socket && this.isConnected) {
      console.log('WebSocket已经连接');
      return;
    }

    try {
      // 创建socket连接
      this.socket = io(API_BASE_URL, {
        transports: ['websocket', 'polling'],
        timeout: 20000,
        forceNew: true
      });

      // 连接成功事件
      this.socket.on('connect', () => {
        console.log('WebSocket连接成功');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // 请求当前状态
        this.requestStatusUpdate();
      });

      // 连接断开事件
      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket连接断开:', reason);
        this.isConnected = false;
        
        // 如果是意外断开，尝试重连
        if (reason === 'io server disconnect') {
          // 服务器主动断开，不重连
          return;
        }
        
        this.attemptReconnect();
      });

      // 连接错误事件
      this.socket.on('connect_error', (error) => {
        console.error('WebSocket连接错误:', error);
        this.isConnected = false;
        this.attemptReconnect();
      });

      // 监听实例状态变化
      this.socket.on('instance_status_change', (data) => {
        console.log('实例状态变化:', data);
        this.emit('instanceStatusChange', data);
      });

      // 监听状态汇总更新
      this.socket.on('status_summary_update', (data) => {
        console.log('状态汇总更新:', data);
        this.emit('statusSummaryUpdate', data);
      });

      // 监听所有实例状态更新
      this.socket.on('instances_status_update', (data) => {
        console.log('所有实例状态更新:', data);
        this.emit('instancesStatusUpdate', data);
      });

    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
    }
  }

  /**
   * 断开WebSocket连接
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
      console.log('WebSocket连接已断开');
    }
  }

  /**
   * 尝试重连
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket重连次数已达上限');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`WebSocket将在${delay}ms后尝试第${this.reconnectAttempts}次重连`);
    
    setTimeout(() => {
      if (!this.isConnected) {
        this.connect();
      }
    }, delay);
  }

  /**
   * 请求状态更新
   */
  requestStatusUpdate() {
    if (this.socket && this.isConnected) {
      this.socket.emit('request_status_update');
    }
  }

  /**
   * 添加事件监听器
   * @param {string} event 事件名称
   * @param {function} callback 回调函数
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  /**
   * 移除事件监听器
   * @param {string} event 事件名称
   * @param {function} callback 回调函数
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * 触发事件
   * @param {string} event 事件名称
   * @param {any} data 事件数据
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`事件监听器执行错误 (${event}):`, error);
        }
      });
    }
  }

  /**
   * 获取连接状态
   */
  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

// 创建全局实例
const websocketService = new WebSocketService();

export default websocketService;
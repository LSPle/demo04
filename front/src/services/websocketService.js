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
    // 添加数据去重机制
    this.lastUpdateTimestamp = 0;
    this.lastDataHash = null;
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
        
        // 触发连接成功事件
        this.emit('connected');
        
        // 请求当前状态
        this.requestStatusUpdate();
      });

      // 连接断开事件
      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket连接断开:', reason);
        this.isConnected = false;
        
        // 触发断开连接事件
        this.emit('disconnected');
        
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
        this.emit('instance_status_change', data);
      });

      // 监听状态汇总更新
      this.socket.on('status_summary_update', (data) => {
        console.log('状态汇总更新:', data);
        this.emit('status_summary_update', data);
      });

      // 监听所有实例状态更新
      this.socket.on('instances_status_update', (data) => {
        console.log('收到实例状态更新:', data);
        
        // 数据去重检查
        if (this.isDuplicateData(data)) {
          console.log('检测到重复数据，跳过处理');
          return;
        }
        
        this.emit('instances_status_update', data);
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
   * 检查是否为重复数据
   * @param {Object} data 接收到的数据
   * @returns {boolean} 是否为重复数据
   */
  isDuplicateData(data) {
    // 检查时间戳
    if (data.timestamp && data.timestamp <= this.lastUpdateTimestamp) {
      return true;
    }
    
    // 生成数据哈希用于比较
    const dataHash = this.generateDataHash(data);
    if (dataHash === this.lastDataHash) {
      return true;
    }
    
    // 更新记录
    if (data.timestamp) {
      this.lastUpdateTimestamp = data.timestamp;
    }
    this.lastDataHash = dataHash;
    
    return false;
  }

  /**
   * 生成数据哈希
   * @param {Object} data 数据对象
   * @returns {string} 数据哈希值
   */
  generateDataHash(data) {
    // 提取关键数据用于哈希计算
    const keyData = {
      instances: data.instances ? data.instances.map(inst => ({
        id: inst.id,
        status: inst.status,
        name: inst.name,
        host: inst.host,
        port: inst.port
      })) : [],
      summary: data.summary || {}
    };
    
    // 简单的哈希算法
    return JSON.stringify(keyData);
  }

  // 已移除getConnectionStatus方法
}

// 创建全局实例
const websocketService = new WebSocketService();

export default websocketService;
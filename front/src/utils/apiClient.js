import { message } from 'antd';
import { API_ENDPOINTS } from '../config/api';

/**
 * 通用API客户端 - 统一处理请求和错误
 */
class ApiClient {
  constructor() {
    this.defaultTimeout = 30000; // 30秒超时
  }

  getUserId() {
    try {
      const uid = localStorage.getItem('userId');
      return uid ? String(uid) : '';
    } catch {
      return '';
    }
  }

  appendUserId(url) {
    const uid = this.getUserId();
    if (!uid) return url;
    return url.includes('?') ? `${url}&userId=${encodeURIComponent(uid)}` : `${url}?userId=${encodeURIComponent(uid)}`;
  }

  /**
   * 通用请求方法
   * @param {string} url - 请求URL
   * @param {Object} options - 请求选项
   * @param {boolean} showError - 是否显示错误消息
   * @returns {Promise<Object>} 响应数据
   */
  async request(url, options = {}, showError = true) {
    const defaultOptions = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: this.defaultTimeout,
      ...options
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), defaultOptions.timeout);
      
      const response = await fetch(url, {
        ...defaultOptions,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: '请求失败' }));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      if (showError) {
        if (error.name === 'AbortError') {
          message.error('请求超时，请检查网络连接');
        } else {
          message.error(error.message || '请求失败，请检查后端服务');
        }
      }
      throw error;
    }
  }

  /**
   * GET请求
   */
  async get(url, showError = true) {
    return this.request(url, { method: 'GET' }, showError);
  }

  /**
   * POST请求
   */
  async post(url, data, showError = true, options = {}) {
    return this.request(url, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options,
    }, showError);
  }

  /**
   * PUT请求
   */
  async put(url, data, showError = true) {
    return this.request(url, {
      method: 'PUT',
      body: JSON.stringify(data)
    }, showError);
  }

  /**
   * DELETE请求
   */
  async delete(url, showError = true) {
    return this.request(url, { method: 'DELETE' }, showError);
  }

  /**
   * 获取实例列表
   */
  async getInstances() {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCES));
  }

  /**
   * 获取实例详情
   */
  async getInstance(id) {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)));
  }

  /**
   * 创建实例
   */
  async createInstance(data) {
    return this.post(this.appendUserId(API_ENDPOINTS.INSTANCES), data);
  }

  /**
   * 更新实例
   */
  async updateInstance(id, data) {
    return this.put(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)), data);
  }

  /**
   * 删除实例
   */
  async deleteInstance(id) {
    return this.delete(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)));
  }

  /**
   * 获取实例数据库列表
   */
  async getInstanceDatabases(id) {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCE_DATABASES(id)));
  }

  /**
   * 获取数据库表列表
   */
  async getDatabaseTables(instanceId, database) {
    return this.get(this.appendUserId(API_ENDPOINTS.DATABASE_TABLES(instanceId, database)));
  }

  /**
   * 获取表结构
   */
  async getTableSchema(instanceId, database, table) {
    return this.get(this.appendUserId(API_ENDPOINTS.TABLE_SCHEMA(instanceId, database, table)));
  }

  /**
   * SQL分析
   */
  async analyzeSql(data) {
    // 统一 DeepSeek 相关请求超时为 300 秒
    return this.post(this.appendUserId(API_ENDPOINTS.SQL_ANALYZE), data, true, { timeout: 300000 });
  }

  /**
   * 执行 SQL（仅 MySQL）
   */
  async executeSql(data) {
    return this.post(this.appendUserId(API_ENDPOINTS.SQL_EXECUTE), data);
  }



  /**
   * 架构分析
   */
  async analyzeArchitecture(instanceId) {
    return this.post(this.appendUserId(API_ENDPOINTS.ARCH_ANALYZE(instanceId)), {}, true, { timeout: 300000 });
  }

  /**
   * 慢日志分析
   */
  async analyzeSlowlog(instanceId) {
    return this.post(this.appendUserId(API_ENDPOINTS.SLOWLOG_ANALYZE(instanceId)), {}, true, { timeout: 300000 });
  }

  /**
   * 获取慢日志列表
   */
  async getSlowlogs(instanceId, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const base = `${API_ENDPOINTS.SLOWLOG_LIST(instanceId)}${queryString ? `?${queryString}` : ''}`;
    return this.get(this.appendUserId(base));
  }

  /**
   * 实例状态检测
   */
  async checkInstanceStatus() {
    const userId = this.getUserId();
    const data = userId ? { userId } : {};
    return this.post(API_ENDPOINTS.MONITOR_CHECK, data);
  }

  /**
   * 获取状态汇总
   */
  async getStatusSummary() {
    // 监控接口无需 userId（全局）
    return this.get(API_ENDPOINTS.MONITOR_SUMMARY);
  }

  /**
   * 获取指标摘要（配置优化）
   */
  async getMetricsSummary(instanceId) {
    return this.get(this.appendUserId(API_ENDPOINTS.METRICS_SUMMARY(instanceId)));
  }

  /**
   * 获取指标建议（DeepSeek，配置优化）
   */
  async getMetricsAdvice(instanceId) {
    return this.post(this.appendUserId(API_ENDPOINTS.METRICS_ADVISE(instanceId)), {}, true, { timeout: 300000 });
  }

}

// 导出单例
export default new ApiClient();
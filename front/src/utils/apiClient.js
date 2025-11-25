import { message } from 'ant-design-vue';
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
   * 获取JWT token
   */
  getToken() {
    try {
      return localStorage.getItem('access_token');
    } catch {
      return null;
    }
  }

  /**
   * 设置JWT token
   */
  setToken(token) {
    try {
      localStorage.setItem('access_token', token);
    } catch (error) {
      console.error('Failed to store token:', error);
    }
  }

  /**
   * 清除JWT token
   */
  clearToken() {
    try {
      localStorage.removeItem('access_token');
      localStorage.removeItem('userId');
    } catch (error) {
      console.error('Failed to clear token:', error);
    }
  }

  /**
   * 通用请求方法
   * @param {string} url - 请求URL
   * @param {Object} options - 请求选项
   * @param {boolean} showError - 是否显示错误消息
   * @returns {Promise<Object>} 响应数据
   */
  async request(url, options = {}, showError = true) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    // 为需要认证的请求添加Authorization头
    const token = this.getToken();
    if (token && !url.includes('/auth/login') && !url.includes('/auth/register')) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeout = options.timeout || this.defaultTimeout;
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const resp = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      });
      clearTimeout(id);

      if (!resp.ok) {
        const text = await resp.text();
        if (showError) message.error(text || `请求失败: ${resp.status}`);
        throw new Error(text || `Request failed: ${resp.status}`);
      }

      const ct = resp.headers.get('content-type') || '';
      if (ct.includes('application/json')) {
        return await resp.json();
      } else {
        return await resp.text();
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        if (showError) message.error('请求超时');
      } else if (showError) {
        message.error(error.message || '请求失败');
      }
      throw error;
    }
  }

  async get(url, showError = true) {
    return this.request(url, { method: 'GET' }, showError);
  }

  async post(url, data, showError = true, options = {}) {
    return this.request(url, { method: 'POST', body: JSON.stringify(data), ...options }, showError);
  }

  async put(url, data, showError = true) {
    return this.request(url, { method: 'PUT', body: JSON.stringify(data) }, showError);
  }

  async delete(url, showError = true) {
    return this.request(url, { method: 'DELETE' }, showError);
  }

  async login(username, password) {
    const data = await this.post(API_ENDPOINTS.AUTH_LOGIN, { username, password });
    if (data && data.access_token && data.user) {
      this.setToken(data.access_token);
      try { localStorage.setItem('userId', String(data.user.id)); } catch {}
    }
    return data;
  }

  async register(username, password) {
    return this.post(API_ENDPOINTS.AUTH_REGISTER, { username, password });
  }

  async logout() {
    try { await this.post(API_ENDPOINTS.AUTH_LOGOUT, {}); } catch {}
    this.clearToken();
  }

  async getCurrentUser() {
    return this.get(API_ENDPOINTS.AUTH_ME);
  }

  async getInstances() {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCES));
  }

  async getInstance(id) {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)));
  }

  async createInstance(data) {
    return this.post(this.appendUserId(API_ENDPOINTS.INSTANCES), data);
  }

  async updateInstance(id, data) {
    return this.put(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)), data);
  }

  async deleteInstance(id) {
    return this.delete(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)));
  }

  async getInstanceDatabases(id) {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCE_DATABASES(id)));
  }

  async getDatabaseTables(instanceId, database) {
    return this.get(this.appendUserId(API_ENDPOINTS.DATABASE_TABLES(instanceId, database)));
  }

  async getTableSchema(instanceId, database, table) {
    return this.get(this.appendUserId(API_ENDPOINTS.TABLE_SCHEMA(instanceId, database, table)));
  }

  async analyzeSql(data) {
    return this.post(this.appendUserId(API_ENDPOINTS.SQL_ANALYZE), data, true, { timeout: 300000 });
  }

  async executeSql(data) {
    return this.post(this.appendUserId(API_ENDPOINTS.SQL_EXECUTE), data);
  }

  /**
   * 架构分析
   */
  async analyzeArchitecture(instanceId, windowSeconds = 6) {
    const baseUrl = API_ENDPOINTS.ARCH_ANALYZE(instanceId);
    const finalUrl = `${baseUrl}?window_s=${windowSeconds}`;
    return this.post(finalUrl, {}, true, { timeout: 300000 });
  }

  /**
   * 架构建议（DeepSeek）
   * 返回纯文本
   */
  async analyzeArchitectureAdvice(instanceId, performance) {
    const url = API_ENDPOINTS.ARCH_ADVISE(instanceId);
    const body = typeof performance === 'object' ? { performance } : {};
    return this.post(url, body, true, { timeout: 300000 });
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
   * 获取配置优化摘要（新路径 /config）
   * 强制窗口采样，默认6秒
   */
  async getConfigSummary(instanceId, windowSeconds = 6) {
    const base = API_ENDPOINTS.CONFIG_SUMMARY(instanceId);
    const n = parseInt(windowSeconds, 10);
    const win = Number.isNaN(n) || n <= 0 ? 6 : Math.max(1, n);
    const qs = new URLSearchParams({ window_s: String(win) }).toString();
    const url = `${base}?${qs}`;
    return this.get(url);
  }

  /**
   * 获取配置优化建议（DeepSeek，新路径 /config）
   */
  async getConfigAdvice(instanceId) {
    return this.post(API_ENDPOINTS.CONFIG_ADVISE(instanceId), {}, true, { timeout: 300000 });
  }

  /**
   * 配置建议（直接拼接前端已有数据，纯文本返回）
   */
  async getConfigAdviceText(instanceId, performance) {
    const body = typeof performance === 'object' ? { performance } : {};
    const url = API_ENDPOINTS.CONFIG_ADVICE(instanceId);
    return this.post(url, body, true, { timeout: 300000 });
  }

}

// 导出单例
export default new ApiClient();

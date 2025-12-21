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
      // 尝试从本地存储中获取用户ID
      const uid = localStorage.getItem('userId');
      // 存在则转换为字符串返回，否则返回空字符串
      return uid ? String(uid) : '';
    } catch {
      return '';
    }
  }

  appendUserId(url) {
    // 获取当前用户ID
    const uid = this.getUserId();
    // 如果没有用户ID，直接返回原URL
    if (!uid) return url;
    // 如果URL已包含参数，追加userId；否则新增参数
    //encodeURIComponent()是javascript的内置函数：把特殊字符变成安全码，方便在网址里传输
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
      console.error('设置access_token失败:', error);
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
    // 1. 设置默认请求头，支持传入自定义头
    console.log('>>> 发起请求:', url, options);

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    // 2. 自动添加认证 Token
    // 为需要认证的请求添加Authorization头(只在“已登录”且访问的不是登录/注册接口时，才给请求头加上 Bearer Token)
    const token = this.getToken();
    if (token && !url.includes('/auth/login') && !url.includes('/auth/register')) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      // 3. 发起 Fetch 请求（已移除复杂的超时控制，简化逻辑）
      const resp = await fetch(url, {
        ...options,
        headers
      });

      // 4. 处理非 200-299 的 HTTP 错误
      if (!resp.ok) {
        const text = await resp.text();
        if (showError) message.error(text || `请求失败: ${resp.status}`);
        throw new Error(text || `Request failed: ${resp.status}`);
      }

      // 5. 根据 Content-Type 自动解析响应内容
      const ct = resp.headers.get('content-type') || '';
      let result;
      if (ct.includes('application/json')) {
        // 如果是 JSON 格式，解析为对象
        result = await resp.json();
      } else {
        // 否则返回纯文本
        result = await resp.text();
      }
      
      console.log('<<< 收到响应:', url, result);
      return result;
    } catch (error) {
      console.error('!!! 请求出错:', url, error);
      // 6. 统一捕获并提示网络错误
      if (showError) {
        message.error(error.message || '请求失败');
      }
      throw error;
    }
  }

  // 封装 GET 请求：获取数据
  // showError: 请求失败时是否自动弹出错误提示，默认为 true
  async get(url, showError = true) {
    return this.request(url, { method: 'GET' }, showError);
  }

  // 封装 POST 请求：提交数据（如创建资源、表单提交）
  // data: 要提交的 JSON 数据对象
  // options: 额外配置，比如超时时间等
  //...options 就是“把剩下的所有设置都塞进去”的意思。
  async post(url, data, showError = true, options = {}) {
    return this.request(url, { method: 'POST', body: JSON.stringify(data), ...options }, showError);
  }

  // 封装 PUT 请求：更新数据
  // data: 要更新的 JSON 数据对象
  async put(url, data, showError = true) {
    return this.request(url, { method: 'PUT', body: JSON.stringify(data) }, showError);
  }

  // 封装 DELETE 请求：删除数据
  async delete(url, showError = true) {
    return this.request(url, { method: 'DELETE' }, showError);
  }

  // --- 业务接口方法 ---

  // 用户登录
  // 1. 发送用户名密码到后端
  // 2. 登录成功后，自动保存 token 和 userId 到本地存储
  async login(username, password) {
    const data = await this.post(API_ENDPOINTS.AUTH_LOGIN, { username, password });
    console.log('登录响应!!!data:', data);     
    if (data && data.access_token && data.user) {
      this.setToken(data.access_token);
      localStorage.setItem('userId', String(data.user.id));
    }
    return data;
  }

  // 用户注册
  async register(username, password) {
    return this.post(API_ENDPOINTS.AUTH_REGISTER, { username, password });
  }

  // 用户退出登录
  // 1. 通知后端注销（可选）
  // 2. 清除本地保存的 token
  async logout() {
    try { await this.post(API_ENDPOINTS.AUTH_LOGOUT, {}); } catch {}
    this.clearToken();
    localStorage.removeItem('userId');
  }

  // 获取当前登录用户信息
  async getCurrentUser() {
    return this.get(API_ENDPOINTS.AUTH_ME);
  }

  // 获取数据库实例列表
  // appendUserId: 自动在 URL 后面拼接 ?userId=xxx 参数，确保只查询当前用户的数据
  async getInstances() {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCES));
  }

  // 获取单个实例详情
  // id: 实例 ID
  async getInstance(id) {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)));
  }

  // 创建新的数据库实例
  // data: 包含 host, port, user, password 等连接信息
  async createInstance(data) {
    return this.post(this.appendUserId(API_ENDPOINTS.INSTANCES), data);
  }

  // 更新实例信息
  // id: 实例 ID
  async updateInstance(id, data) {
    return this.put(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)), data);
  }

  // 删除实例
  // id: 实例 ID
  async deleteInstance(id) {
    return this.delete(this.appendUserId(API_ENDPOINTS.INSTANCE_DETAIL(id)));
  }

  // 获取指定实例下的所有数据库列表
  async getInstanceDatabases(id) {
    return this.get(this.appendUserId(API_ENDPOINTS.INSTANCE_DATABASES(id)));
  }

  // 获取指定数据库下的所有表名
  // instanceId: 实例 ID
  // database: 数据库名
  async getDatabaseTables(instanceId, database) {
    return this.get(this.appendUserId(API_ENDPOINTS.DATABASE_TABLES(instanceId, database)));
  }

  // 获取指定表的结构信息（字段、类型等）
  // table: 表名
  async getTableSchema(instanceId, database, table) {
    return this.get(this.appendUserId(API_ENDPOINTS.TABLE_SCHEMA(instanceId, database, table)));
  }
  
  //--------------------------------------------------------------------------------------------------------------
  
  // 智能 SQL 分析
  // 发送 SQL 语句给后端 AI 模型进行分析优化
  // timeout: 300000ms (5分钟)，因为 AI 分析可能比较耗时
  async analyzeSql(data) {
    return this.post(this.appendUserId(API_ENDPOINTS.SQL_ANALYZE), data, true, { timeout: 300000 });
  }

  // 执行 SQL 语句
  // 直接在数据库上运行 SQL 并返回结果
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

import apiClient from './apiClient';

// 全局实例状态管理 


// 全局状态对象
window.globalInstances = {
  allInstances: [],        // 所有实例的基本信息
  runningInstances: [],    // 运行中的实例列表
  statusMap: {},           // 实例状态映射 {instanceId: true/false}
  loaded: false,           // 是否已加载数据
  loading: false,          // 是否正在加载
  lastUpdateTime: null,    // 最后更新时间
  loadingPromise: null     // 当前加载任务的Promise（单飞模式）
};

/**
 * 加载实例数据和状态信息（单飞：并发时复用同一个请求）
 * @param {boolean} showMessage 是否显示加载消息
 * @returns {Promise<boolean>} 是否加载成功
 */
export async function loadInstances(showMessage = false) {
  // 单飞：已有加载任务时复用同一个Promise，避免并发导致返回false
  // 防止重复请求，避免重复加载数据
  if (window.globalInstances.loadingPromise) {
    try {
      await window.globalInstances.loadingPromise;
      return true;
    } catch (error) {
      return false;
    }
  }

  window.globalInstances.loading = true;

  const loadingTask = (async () => {
    try {
      // 1. 获取所有实例
      const instancesData = await apiClient.getInstances();
      let instances = [];
      if (Array.isArray(instancesData)) {
        instances = instancesData;
      } else if (instancesData && Array.isArray(instancesData.instances)) {
        instances = instancesData.instances;
      }

      // 2. 获取实例状态
      const statusRes = await apiClient.checkInstanceStatus();
      // 获取状态列表，如果没获取到（undefined或null）就给一个空数组，防止报错
      let statuses = [];
      if (statusRes && statusRes.statuses) {
        statuses = statusRes.statuses;
      }

      // 3. 构建状态映射
      const statusMap = {};
      statuses.forEach(status => {
        if (status && typeof status.id != null) {
          statusMap[status.id] = Boolean(status.ok);
        }
      });

      // 4. 过滤运行中的实例
      const runningInstances = instances.filter(instance => 
        statusMap[instance.id] === true
      );

      // 5. 更新全局状态
      window.globalInstances.allInstances = instances;
      window.globalInstances.runningInstances = runningInstances;
      window.globalInstances.statusMap = statusMap;
      window.globalInstances.loaded = true;
      window.globalInstances.lastUpdateTime = new Date();

      if (showMessage && window.message) {
        window.message.success('实例数据加载成功');
      }
    } catch (error) {
      console.error('加载实例数据失败:', error);
      if (showMessage && window.message) {
        window.message.error('加载实例数据失败: ' + (error.message || '未知错误'));
      }
      // 抛出错误以便外层返回false
      throw error;
    } finally {
      window.globalInstances.loading = false;
      window.globalInstances.loadingPromise = null;
    }
  })();

  // 记录当前加载任务Promise
  window.globalInstances.loadingPromise = loadingTask;

  // 确保加载任务完成后返回结果（await 用来卡住后续代码执行，直到加载完成）
  try {
    await loadingTask;
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * 获取运行中的实例列表
 * @returns {Array} 运行中的实例数组
 */
export function getRunningInstances() {
  return window.globalInstances.runningInstances || [];
}

/**
 * 获取所有实例列表
 * @returns {Array} 所有实例数组
 */
export function getAllInstances() {
  return window.globalInstances.allInstances || [];
}

/**
 * 获取实例状态映射
 * @returns {Object} 状态映射对象
 */
export function getStatusMap() {
  return window.globalInstances.statusMap || {};
}

/**
 * 检查数据是否已加载
 * @returns {boolean} 是否已加载
 */
export function isLoaded() {
  return window.globalInstances.loaded;
}

/**
 * 检查是否正在加载
 * @returns {boolean} 是否正在加载
 */
export function isLoading() {
  return window.globalInstances.loading;
}

/**
 * 检查数据是否过期（超过5分钟）
 * @returns {boolean} 是否过期
 */
export function isDataExpired() {
  if (!window.globalInstances.lastUpdateTime) {
    return true;
  }
  const now = new Date();
  const diff = now - window.globalInstances.lastUpdateTime;
  return diff > 5 * 60 * 1000; // 5分钟
}

/**
 * 清空全局数据（用于强制重新加载）
 */
export function clearGlobalData() {
  window.globalInstances.allInstances = [];
  window.globalInstances.runningInstances = [];
  window.globalInstances.statusMap = {};
  window.globalInstances.loaded = false;
  window.globalInstances.loading = false;
  window.globalInstances.lastUpdateTime = null;
  window.globalInstances.loadingPromise = null;
  
  // 派发全局事件，通知各页面清空本地下拉缓存
  try {
    window.dispatchEvent(new CustomEvent('instances-cache-cleared'));
  } catch (e) {}
}

/**
 * 智能加载实例数据
 * 如果数据未加载或已过期，则重新加载
 * @param {boolean} showMessage 是否显示消息
 * @returns {Promise<boolean>} 是否成功
 */
export async function ensureInstancesLoaded(showMessage = false) {
  if (!isLoaded() || isDataExpired()) {
    return await loadInstances(showMessage);
  }
  return true;
}

// 导出默认对象，方便使用
export default {
  loadInstances,
  getRunningInstances,
  getAllInstances,
  getStatusMap,
  isLoaded,
  isLoading,
  isDataExpired,
  clearGlobalData,
  ensureInstancesLoaded
};
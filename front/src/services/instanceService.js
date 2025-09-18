import apiClient from '../utils/apiClient';

/**
 * 实例服务层 - 处理所有与实例相关的API调用
 */
export const instanceService = {
  /**
   * 获取实例列表
   * @returns {Promise<Array>} 实例列表数组
   */
  async fetchInstances() {
    try {
      const data = await apiClient.getInstances();
      // 处理API响应数据 - 后端直接返回数组
      return Array.isArray(data) ? data : (Array.isArray(data.instances) ? data.instances : []);
    } catch (error) {
      console.error('获取实例列表失败:', error);
      throw new Error('获取实例列表失败');
    }
  },

  /**
   * 刷新实例状态
   * @returns {Promise<Object>} 状态检测结果
   */
  async refreshInstanceStatus() {
    try {
      const result = await apiClient.checkInstanceStatus();
      return result;
    } catch (error) {
      console.error('刷新实例状态失败:', error);
      throw new Error('刷新实例状态失败，请检查后端服务');
    }
  }
};

export default instanceService;
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { message } from 'antd';
import { API_ENDPOINTS } from '../config/api';

// 创建实例上下文
const InstanceContext = createContext();

// 实例状态管理Provider
export const InstanceProvider = ({ children }) => {
  const [instances, setInstances] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  // 获取实例列表
  const fetchInstances = useCallback(async (showMessage = false) => {
    try {
      setLoading(true);
      const response = await fetch(API_ENDPOINTS.INSTANCES);
      if (!response.ok) {
        throw new Error('获取实例列表失败');
      }
      const data = await response.json();
      const instanceList = Array.isArray(data) ? data : (Array.isArray(data.instances) ? data.instances : []);
      setInstances(instanceList);
      setLastUpdated(new Date());
      if (showMessage) {
        message.success('实例列表已更新');
      }
    } catch (error) {
      console.error('获取实例列表失败:', error);
      if (showMessage) {
        message.error(`获取实例列表失败：${error.message}`);
      }
      setInstances([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 获取运行中的实例选项
  const getRunningInstanceOptions = useCallback(() => {
    return instances
      .filter(inst => inst.status === 'running')
      .map(inst => ({
        value: String(inst.id),
        label: `${inst.instanceName} (${inst.dbType}) ${inst.host}:${inst.port}`,
        status: inst.status,
        ...inst
      }));
  }, [instances]);

  // 获取所有实例选项
  const getAllInstanceOptions = useCallback(() => {
    return instances.map(inst => ({
      value: String(inst.id),
      label: `${inst.instanceName} (${inst.dbType}) ${inst.host}:${inst.port}`,
      status: inst.status,
      ...inst
    }));
  }, [instances]);

  // 刷新实例列表（手动刷新，显示消息）
  const refreshInstances = useCallback(() => {
    fetchInstances(true);
  }, [fetchInstances]);

  // 静默刷新实例列表（自动刷新，不显示消息）
  const silentRefreshInstances = useCallback(() => {
    fetchInstances(false);
  }, [fetchInstances]);

  // 添加实例后的回调
  const onInstanceAdded = useCallback(() => {
    fetchInstances(false);
  }, [fetchInstances]);

  // 删除实例后的回调
  const onInstanceDeleted = useCallback(() => {
    fetchInstances(false);
  }, [fetchInstances]);

  // 更新实例后的回调
  const onInstanceUpdated = useCallback(() => {
    fetchInstances(false);
  }, [fetchInstances]);

  // 组件挂载时获取实例列表
  useEffect(() => {
    fetchInstances(false);
  }, [fetchInstances]);

  // 定期自动刷新实例列表（每30秒）
  useEffect(() => {
    const interval = setInterval(() => {
      silentRefreshInstances();
    }, 30000);

    return () => clearInterval(interval);
  }, [silentRefreshInstances]);

  const value = {
    instances,
    loading,
    lastUpdated,
    getRunningInstanceOptions,
    getAllInstanceOptions,
    refreshInstances,
    silentRefreshInstances,
    onInstanceAdded,
    onInstanceDeleted,
    onInstanceUpdated
  };

  return (
    <InstanceContext.Provider value={value}>
      {children}
    </InstanceContext.Provider>
  );
};

// 使用实例上下文的Hook
export const useInstances = () => {
  const context = useContext(InstanceContext);
  if (!context) {
    throw new Error('useInstances must be used within an InstanceProvider');
  }
  return context;
};

export default InstanceContext;
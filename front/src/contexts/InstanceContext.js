import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { message } from 'antd';
import apiClient from '../utils/apiClient';
import websocketService from '../services/websocketService';

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
      const data = await apiClient.getInstances();
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

  // 工具函数：根据 id 合并单个实例（新增或替换）
  const upsertInstance = useCallback((item) => {
    if (!item || typeof item.id === 'undefined') return;
    setInstances(prev => {
      const exists = prev.some(i => i.id === item.id);
      const next = exists ? prev.map(i => (i.id === item.id ? { ...i, ...item } : i)) : [...prev, item];
      return next;
    });
    setLastUpdated(new Date());
  }, []);

  // 工具函数：根据 id 删除实例
  const removeInstanceById = useCallback((id) => {
    if (typeof id === 'undefined' || id === null) return;
    const numId = typeof id === 'string' ? parseInt(id, 10) : id;
    setInstances(prev => prev.filter(i => i.id !== numId));
    setLastUpdated(new Date());
  }, []);

  // 添加实例后的回调（支持增量合并）
  const onInstanceAdded = useCallback((payload) => {
    if (payload && payload.id !== undefined) {
      upsertInstance(payload);
    } else {
      fetchInstances(false);
    }
  }, [fetchInstances, upsertInstance]);

  // 删除实例后的回调（支持增量合并）
  const onInstanceDeleted = useCallback((payload) => {
    // 支持传入 id 或 { id }
    const id = typeof payload === 'object' ? payload?.id : payload;
    if (id !== undefined && id !== null) {
      removeInstanceById(id);
    } else {
      fetchInstances(false);
    }
  }, [fetchInstances, removeInstanceById]);

  // 更新实例后的回调（支持增量合并）
  const onInstanceUpdated = useCallback((payload) => {
    if (payload && payload.id !== undefined) {
      upsertInstance(payload);
    } else {
      fetchInstances(false);
    }
  }, [fetchInstances, upsertInstance]);

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

  // 订阅 WebSocketService 的本地事件总线，进行增量更新
  useEffect(() => {
    const handleAdded = (data) => onInstanceAdded(data);
    const handleDeleted = (data) => onInstanceDeleted(data);
    const handleUpdated = (data) => onInstanceUpdated(data);

    websocketService.on('instanceAdded', handleAdded);
    websocketService.on('instanceDeleted', handleDeleted);
    websocketService.on('instanceUpdated', handleUpdated);

    return () => {
      websocketService.off('instanceAdded', handleAdded);
      websocketService.off('instanceDeleted', handleDeleted);
      websocketService.off('instanceUpdated', handleUpdated);
    };
  }, [onInstanceAdded, onInstanceDeleted, onInstanceUpdated]);

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
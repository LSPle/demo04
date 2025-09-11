import { useState, useEffect, useCallback } from 'react';
import { message } from 'antd';
import apiClient from '../utils/apiClient';

/**
 * 通用API数据获取Hook
 * @param {Function} apiCall - API调用函数
 * @param {Array} dependencies - 依赖数组
 * @param {Object} options - 配置选项
 * @returns {Object} { data, loading, error, refetch }
 */
export const useApiData = (apiCall, dependencies = [], options = {}) => {
  const {
    immediate = true,
    showError = true,
    initialData = null,
    onSuccess,
    onError
  } = options;

  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!apiCall) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const result = await apiCall();
      setData(result);
      
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err) {
      setError(err);
      
      if (showError) {
        message.error(err.message || '数据获取失败');
      }
      
      if (onError) {
        onError(err);
      }
    } finally {
      setLoading(false);
    }
  }, [apiCall, showError, onSuccess, onError]);

  useEffect(() => {
    if (immediate) {
      fetchData();
    }
  }, dependencies);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
    setData
  };
};

/**
 * 实例列表数据Hook
 */
export const useInstances = (options = {}) => {
  return useApiData(
    () => apiClient.getInstances(),
    [],
    {
      initialData: [],
      ...options
    }
  );
};

/**
 * 实例详情数据Hook
 */
export const useInstance = (instanceId, options = {}) => {
  return useApiData(
    instanceId ? () => apiClient.getInstance(instanceId) : null,
    [instanceId],
    options
  );
};

/**
 * 实例数据库列表Hook
 */
export const useInstanceDatabases = (instanceId, options = {}) => {
  return useApiData(
    instanceId ? () => apiClient.getInstanceDatabases(instanceId) : null,
    [instanceId],
    {
      initialData: { databases: [] },
      ...options
    }
  );
};

/**
 * 数据库表列表Hook
 */
export const useDatabaseTables = (instanceId, database, options = {}) => {
  return useApiData(
    instanceId && database ? () => apiClient.getDatabaseTables(instanceId, database) : null,
    [instanceId, database],
    {
      initialData: { tables: [] },
      ...options
    }
  );
};

/**
 * 慢日志列表Hook
 */
export const useSlowlogs = (instanceId, params = {}, options = {}) => {
  const [filters, setFilters] = useState(params);
  
  const result = useApiData(
    instanceId ? () => apiClient.getSlowlogs(instanceId, filters) : null,
    [instanceId, JSON.stringify(filters)],
    {
      initialData: { items: [], total: 0, overview: {} },
      immediate: !!instanceId,
      ...options
    }
  );

  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  return {
    ...result,
    filters,
    updateFilters
  };
};

/**
 * 分析操作Hook
 */
export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const analyze = useCallback(async (apiCall, successMessage = '分析完成') => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await apiCall();
      setResult(data);
      
      message.success(successMessage);
      return data;
    } catch (err) {
      setError(err);
      message.error(err.message || '分析失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    loading,
    result,
    error,
    analyze,
    reset
  };
};

/**
 * 表单提交Hook
 */
export const useFormSubmit = () => {
  const [loading, setLoading] = useState(false);

  const submit = useCallback(async (apiCall, successMessage = '操作成功', onSuccess) => {
    try {
      setLoading(true);
      
      const result = await apiCall();
      
      message.success(successMessage);
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err) {
      message.error(err.message || '操作失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    submit
  };
};
import { useState, useEffect, useCallback } from 'react';

/**
 * 防抖Hook - 延迟更新值直到指定时间内没有新的更新
 * @param {any} value - 需要防抖的值
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {any} 防抖后的值
 */
export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

/**
 * 防抖回调Hook - 返回一个防抖的回调函数
 * @param {Function} callback - 需要防抖的回调函数
 * @param {number} delay - 延迟时间（毫秒）
 * @param {Array} deps - 依赖数组
 * @returns {Function} 防抖后的回调函数
 */
export const useDebounceCallback = (callback, delay, deps = []) => {
  const [debounceTimer, setDebounceTimer] = useState(null);

  useEffect(() => {
    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
    };
  }, [debounceTimer]);

  // 使用useCallback确保依赖变化时回调函数能正确更新
  const debouncedCallback = useCallback((...args) => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    const timer = setTimeout(() => {
      callback(...args);
    }, delay);

    setDebounceTimer(timer);
  }, [callback, delay, debounceTimer, ...deps]);

  return debouncedCallback;
};

export default useDebounce;
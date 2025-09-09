// API配置
// CloudBase云托管服务地址 - 使用相对路径，通过CloudBase Framework路由
// 优先从环境变量读取后端地址，构建时设置 REACT_APP_API_BASE_URL；为空则走相对路径
const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/+$/, '');

export const API_ENDPOINTS = {
  INSTANCES: `/api/instances`,
  INSTANCE_DATABASES: (id) => `/api/instances/${id}/databases`,
  INSTANCE_DETAIL: (id) => `/api/instances/${id}`,
  DATABASE_TABLES: (instanceId, database) => `/api/instances/${instanceId}/databases/${encodeURIComponent(database)}/tables`,
  TABLE_SCHEMA: (instanceId, database, table) => `/api/instances/${instanceId}/databases/${encodeURIComponent(database)}/tables/${encodeURIComponent(table)}/schema`,
  SQL_EXECUTE: `/api/sql/execute`,
  SQL_ANALYZE: `/api/sql/analyze`,
  // 新增：配置分析接口（POST）
  CONFIG_ANALYZE: (id) => `/api/instances/${id}/config/analyze`,
  // 新增：架构分析接口（POST）
  ARCH_ANALYZE: (id) => `/api/instances/${id}/arch/analyze`,
  SLOWLOG_ANALYZE: (id) => `/api/instances/${id}/slowlog/analyze`,
  // 新增：慢日志列表（GET）
  SLOWLOG_LIST: (id) => `/api/instances/${id}/slowlog`,
  METRICS: `/api/metrics`,
};

export default API_BASE_URL;
// API配置
// 后端服务地址 - 优先从环境变量读取，默认使用Zeabur部署的后端地址
const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || 'https://1049726439demo.zeabur.app').replace(/\/+$/, '');

export const API_ENDPOINTS = {
  INSTANCES: `${API_BASE_URL}/api/instances`,
  INSTANCE_DATABASES: (id) => `${API_BASE_URL}/api/instances/${id}/databases`,
  INSTANCE_DETAIL: (id) => `${API_BASE_URL}/api/instances/${id}`,
  DATABASE_TABLES: (instanceId, database) => `${API_BASE_URL}/api/instances/${instanceId}/databases/${encodeURIComponent(database)}/tables`,
  TABLE_SCHEMA: (instanceId, database, table) => `${API_BASE_URL}/api/instances/${instanceId}/databases/${encodeURIComponent(database)}/tables/${encodeURIComponent(table)}/schema`,
  SQL_EXECUTE: `${API_BASE_URL}/api/sql/execute`,
  SQL_ANALYZE: `${API_BASE_URL}/api/sql/analyze`,
  // 新增：配置分析接口（POST）
  CONFIG_ANALYZE: (id) => `${API_BASE_URL}/api/instances/${id}/config/analyze`,
  // 新增：架构分析接口（POST）
  ARCH_ANALYZE: (id) => `${API_BASE_URL}/api/instances/${id}/arch/analyze`,
  SLOWLOG_ANALYZE: (id) => `${API_BASE_URL}/api/instances/${id}/slowlog/analyze`,
  // 新增：慢日志列表（GET）
  SLOWLOG_LIST: (id) => `${API_BASE_URL}/api/instances/${id}/slowlog`,
  METRICS: `${API_BASE_URL}/api/metrics`,
};

export default API_BASE_URL;
// API配置
// 后端服务地址 - 优先从环境变量读取，默认使用本地后端地址
// 注意：开发模式下后端 run.py 默认端口为 5000
const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000').replace(/\/+$/, '');

export const API_ENDPOINTS = {
  INSTANCES: `${API_BASE_URL}/api/instances`,
  INSTANCE_DATABASES: (id) => `${API_BASE_URL}/api/instances/${id}/databases`,
  INSTANCE_DETAIL: (id) => `${API_BASE_URL}/api/instances/${id}`,
  DATABASE_TABLES: (instanceId, database) => `${API_BASE_URL}/api/instances/${instanceId}/databases/${encodeURIComponent(database)}/tables`,
  TABLE_SCHEMA: (instanceId, database, table) => `${API_BASE_URL}/api/instances/${instanceId}/databases/${encodeURIComponent(database)}/tables/${encodeURIComponent(table)}/schema`,
  SQL_EXECUTE: `${API_BASE_URL}/api/sql/execute`,
  SQL_ANALYZE: `${API_BASE_URL}/api/sql/analyze`,

  // 新增：架构分析接口（POST）
  ARCH_ANALYZE: (id) => `${API_BASE_URL}/api/instances/${id}/arch/analyze`,
  SLOWLOG_ANALYZE: (id) => `${API_BASE_URL}/api/instances/${id}/slowlog/analyze`,
  // 新增：慢日志列表（GET）
  SLOWLOG_LIST: (id) => `${API_BASE_URL}/api/instances/${id}/slowlog`,
  // 新增：实例状态检测接口
  MONITOR_CHECK: `${API_BASE_URL}/api/monitor/instances/check`,
  MONITOR_SUMMARY: `${API_BASE_URL}/api/monitor/instances/summary`,
  METRICS: `${API_BASE_URL}/api/metrics`,

  // 新增：指标摘要与建议（配置优化）
  METRICS_SUMMARY: (id) => `${API_BASE_URL}/api/instances/${id}/metrics/summary`,
  METRICS_ADVISE: (id) => `${API_BASE_URL}/api/instances/${id}/metrics/advise`,
};

export default API_BASE_URL;
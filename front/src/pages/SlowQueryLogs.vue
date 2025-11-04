<template>
  <div class="slowlog-container">
    <!-- 页面标题区域 -->
    <div class="config-header">
      <div class="header-content">
        <div class="title-area">
          <h2 class="config-title">慢查询日志</h2>
          <p class="config-desc">查看和分析数据库慢查询日志</p>
        </div>
      </div>
    </div>

    <!-- 操作区卡片：实例选择 + 按钮 -->
    <div class="control-section">
      <a-card title="实例选择与操作" class="control-card">
        <a-space>
          <a-select v-model:value="selectedInstance" style="min-width: 280px" placeholder="选择实例" class="instance-select">
            <a-select-option v-for="opt in instanceOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-select-option>
          </a-select>
          <a-button @click="loadSlowlogs" :disabled="!selectedInstance" class="load-btn">获取慢日志</a-button>
          <a-button type="primary" @click="analyzeSlowlog" :disabled="!selectedInstance" class="analyze-btn">分析慢日志</a-button>
        </a-space>
      </a-card>
    </div>

    <!-- 慢日志卡片：表格展示 -->
    <div class="data-section">
      <a-card title="慢查询日志" :loading="logsLoading" class="data-card">
        <div class="table-container">
          <a-table :columns="columns" :data-source="logs" rowKey="_rowKey" :pagination="{ pageSize: 8 }"/>
        </div>
      </a-card>
    </div>

    <!-- 分析结果卡片 -->
    <div v-if="analysis" class="analysis-section">
      <a-card title="分析结果" class="analysis-card">
        <div class="analysis-content">
          <pre class="analysis-result">{{ pretty(analysis) }}</pre>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';
import globalInstances from '../utils/globalInstances';

let cacheClearedHandler = null;

const logsLoading = ref(false);
const analysisLoading = ref(false);
const instanceOptions = ref([]);
const selectedInstance = ref('');
const logs = ref([]);
const analysis = ref(null);

// 简化列定义：依赖归一化后的数据字段，避免在列中写逻辑
const columns = [
  { title: 'SQL', dataIndex: 'query', key: 'query', ellipsis: true },
  { title: '次数', dataIndex: 'count', key: 'count', width: 80 },
  { title: '平均耗时(ms)', dataIndex: 'avg_latency_ms', key: 'avg_latency_ms', width: 140 },
  { title: '扫描行数', dataIndex: 'rows_examined_avg', key: 'rows_examined_avg', width: 120 },
];

function pretty(obj) { try { return JSON.stringify(obj, null, 2); } catch { return String(obj); } }

function toNumber(val, def = 0) {
  const n = Number(val);
  return Number.isFinite(n) ? n : def;
}

function round2(val) {
  const n = Number(val);
  if (!Number.isFinite(n)) return 0;
  return Math.round(n * 100) / 100;
}

function normalizeItem(r, idx) {
  // 原始字段先展开，后续归一化字段覆盖，避免被原值反向覆盖
  const base = { ...r };

  const query = base.query ?? base.sql ?? base.sql_text ?? '-';
  // 次数：优先 count，其次 count_star，最后默认 1
  let count = Number(base.count);
  if (!Number.isFinite(count)) count = Number(base.count_star);
  if (!Number.isFinite(count)) count = 1;

  let avgMs = base.avg_latency_ms;
  if (!Number.isFinite(Number(avgMs))) {
    const qsec = base.query_time; // 秒
    const seconds = toNumber(qsec, 0);
    avgMs = round2(seconds * 1000);
  }

  // 扫描行数：直接使用 rows_examined_avg，如果无效则默认 0
  let rowsExamined = Number(base.rows_examined_avg);
  if (!Number.isFinite(rowsExamined)) rowsExamined = 0;

  return {
    ...base,
    _rowKey: idx,
    query,
    count,
    avg_latency_ms: round2(avgMs),
    rows_examined_avg: rowsExamined,
  };
}

async function loadInstances() {
  try {
    // 确保全局数据已加载
    await globalInstances.ensureInstancesLoaded();
    
    // 获取运行中的实例
    const runningInstances = globalInstances.getRunningInstances();
    
    // 格式化选项
    instanceOptions.value = runningInstances.map(i => ({
      value: String(i.id),
      label: `${i.instanceName} (${i.dbType}) ${i.host}:${i.port}`
    }));
  } catch {
    instanceOptions.value = [];
  }
}

async function loadSlowlogs() {
  if (!selectedInstance.value) { message.warning('请选择实例'); return; }
  try {
    logsLoading.value = true;
    const res = await apiClient.getSlowlogs(Number(selectedInstance.value));
    const items = Array.isArray(res?.items) ? res.items : (Array.isArray(res) ? res : []);
    logs.value = items.map((r, idx) => normalizeItem(r, idx));
    message.success('慢日志已获取');
  } catch (e) {
    logs.value = [];
  } finally {
    logsLoading.value = false;
  }
}

async function analyzeSlowlog() {
  if (!selectedInstance.value) { message.warning('请选择实例'); return; }
  try {
    analysisLoading.value = true;
    const res = await apiClient.analyzeSlowlog(Number(selectedInstance.value));
    analysis.value = res;
    message.success('慢日志分析完成');
  } catch (e) {
    analysis.value = null;
  } finally {
    analysisLoading.value = false;
  }
}

onMounted(() => {
  loadInstances();
  cacheClearedHandler = () => {
    instanceOptions.value = [];
    loadInstances();
  };
  window.addEventListener('instances-cache-cleared', cacheClearedHandler);
});

onUnmounted(() => {
  if (cacheClearedHandler) {
    window.removeEventListener('instances-cache-cleared', cacheClearedHandler);
  }
});
</script>

<style scoped>
/* 慢查询日志页面样式 */
.slowlog-container {
  background: none;
  padding: 0;
}

/* 页面标题区域 */
.config-header {
  background: rgba(255, 255, 255, 0.95);
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 24px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.config-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.config-desc {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: #666;
  opacity: 0.9;
}

/* 控制区域 */
.control-section {
  margin-bottom: 24px;
}

.control-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.control-card .ant-card-head {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 24px;
}

.control-card .ant-card-head-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.control-card .ant-card-body {
  padding: 20px 24px;
}

.instance-select {
  border-radius: 8px;
}

.load-btn, .analyze-btn {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.load-btn:hover, .analyze-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 数据区域 */
.data-section {
  margin-bottom: 24px;
}

.data-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.data-card .ant-card-head {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 24px;
}

.data-card .ant-card-head-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.data-card .ant-card-body {
  padding: 20px 24px;
}

.table-container {
  border-radius: 8px;
  overflow: hidden;
}

/* 分析结果区域 */
.analysis-section {
  margin-bottom: 24px;
}

.analysis-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.analysis-card .ant-card-head {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 24px;
}

.analysis-card .ant-card-head-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.analysis-card .ant-card-body {
  padding: 20px 24px;
}

.analysis-content {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e9ecef;
}

.analysis-result {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: none;
}

/* 表格样式优化 */
:deep(.ant-table-cell) {
  word-break: break-word;
  padding: 12px 16px;
}

:deep(.ant-table-thead > tr > th) {
  background: #fafafa;
  font-weight: 600;
  color: #262626;
  border-bottom: 2px solid #f0f0f0;
}

:deep(.ant-table-tbody > tr:hover > td) {
  background: #f5f5f5;
}

:deep(.ant-pagination) {
  margin-top: 16px;
  text-align: center;
}

/* 动画效果 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.control-section,
.data-section,
.analysis-section {
  animation: fadeInUp 0.6s ease-out;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .config-header {
    padding: 16px;
    margin-bottom: 16px;
  }
  
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .config-title {
    font-size: 20px;
  }
  
  .config-desc {
    font-size: 12px;
  }
  
  .control-section,
  .data-section,
  .analysis-section {
    margin-bottom: 16px;
  }
  
  .control-card .ant-card-head,
  .data-card .ant-card-head,
  .analysis-card .ant-card-head {
    padding: 12px 16px;
  }
  
  .control-card .ant-card-body,
  .data-card .ant-card-body,
  .analysis-card .ant-card-body {
    padding: 16px;
  }
  
  .instance-select {
    min-width: 200px !important;
  }
  
  .ant-space {
    flex-wrap: wrap;
  }
}

@media (max-width: 480px) {
  .config-header {
    padding: 12px;
  }
  
  .config-title {
    font-size: 18px;
  }
  
  .control-card .ant-card-head,
  .data-card .ant-card-head,
  .analysis-card .ant-card-head {
    padding: 8px 12px;
  }
  
  .control-card .ant-card-body,
  .data-card .ant-card-body,
  .analysis-card .ant-card-body {
    padding: 12px;
  }
  
  .instance-select {
    min-width: 150px !important;
  }
  
  .load-btn, .analyze-btn {
    font-size: 12px;
    height: 32px;
    padding: 0 12px;
  }
  
  .analysis-content {
    padding: 12px;
  }
  
  .analysis-result {
    font-size: 12px;
  }
}
</style>
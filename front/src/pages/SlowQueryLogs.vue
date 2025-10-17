<template>
  <a-space direction="vertical" style="width:100%">
    <!-- 操作区卡片：实例选择 + 按钮 -->
    <a-card title="实例选择与操作">
      <a-space>
        <a-select v-model:value="selectedInstance" style="min-width: 280px" placeholder="选择实例">
          <a-select-option v-for="opt in instanceOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </a-select-option>
        </a-select>
        <a-button @click="loadSlowlogs" :disabled="!selectedInstance">获取慢日志</a-button>
        <a-button type="primary" @click="analyzeSlowlog" :disabled="!selectedInstance">分析慢日志</a-button>
      </a-space>
    </a-card>

    <!-- 慢日志卡片：表格展示 -->
    <a-card title="慢查询日志" :loading="logsLoading">
      <a-table :columns="columns" :data-source="logs" rowKey="_rowKey" :pagination="{ pageSize: 8 }"/>
    </a-card>

    <!-- 分析结果卡片 -->
    <a-card v-if="analysis" title="分析结果">
      <pre style="white-space: pre-wrap">{{ pretty(analysis) }}</pre>
    </a-card>
  </a-space>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';

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
  { title: '平均耗时(ms)', dataIndex: 'avg_time_ms', key: 'avg_time_ms', width: 140 },
  { title: '扫描行数', dataIndex: 'rows_examined', key: 'rows_examined', width: 120 },
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

  let avgMs = base.avg_time_ms;
  if (!Number.isFinite(Number(avgMs))) avgMs = base.avg_latency_ms;
  if (!Number.isFinite(Number(avgMs))) {
    const qsec = base.query_time; // 秒
    const seconds = toNumber(qsec, 0);
    avgMs = round2(seconds * 1000);
  }

  // 扫描行数：优先 rows_examined，其次 rows_examined_avg，最后默认 0
  let rowsExamined = Number(base.rows_examined);
  if (!Number.isFinite(rowsExamined)) rowsExamined = Number(base.rows_examined_avg);
  if (!Number.isFinite(rowsExamined)) rowsExamined = 0;

  return {
    ...base,
    _rowKey: idx,
    query,
    count,
    avg_time_ms: round2(avgMs),
    rows_examined: rowsExamined,
  };
}

async function loadInstances() {
  try {
    const data = await apiClient.getInstances();
    const list = Array.isArray(data) ? data : (Array.isArray(data?.instances) ? data.instances : []);
    instanceOptions.value = list.filter(i => i.status === 'running').map(i => ({
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

onMounted(() => { loadInstances(); });
</script>

<style scoped>
:deep(.ant-table-cell) {
  word-break: break-word;
}
/* 卡片间距优化 */
.ant-card + .ant-card { margin-top: 12px; }
</style>
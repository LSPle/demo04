<template>
  <a-card title="慢查询日志" :loading="loading">
    <a-space direction="vertical" style="width:100%">
      <a-space>
        <a-select v-model:value="selectedInstance" style="min-width: 280px" placeholder="选择实例">
          <a-select-option v-for="opt in instanceOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </a-select-option>
        </a-select>
        <a-button @click="loadSlowlogs" :disabled="!selectedInstance">获取慢日志</a-button>
        <a-button type="primary" @click="analyzeSlowlog" :disabled="!selectedInstance">分析慢日志</a-button>
      </a-space>

      <a-table :columns="columns" :data-source="logs" rowKey="_rowKey" :pagination="{ pageSize: 8 }"/>

      <a-card v-if="analysis" title="分析结果" style="margin-top: 12px">
        <pre style="white-space: pre-wrap">{{ pretty(analysis) }}</pre>
      </a-card>
    </a-space>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';

const loading = ref(false);
const instanceOptions = ref([]);
const selectedInstance = ref('');
const logs = ref([]);
const analysis = ref(null);

const columns = [
  { title: 'SQL', dataIndex: 'query', key: 'query' },
  { title: '次数', dataIndex: 'count', key: 'count', width: 80 },
  { title: '平均耗时(ms)', dataIndex: 'avg_time_ms', key: 'avg_time_ms', width: 140 },
  { title: '扫描行数', dataIndex: 'rows_examined', key: 'rows_examined', width: 120 },
];

function pretty(obj) { try { return JSON.stringify(obj, null, 2); } catch { return String(obj); } }

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
    loading.value = true;
    const res = await apiClient.getSlowlogs(Number(selectedInstance.value));
    const items = Array.isArray(res?.items) ? res.items : (Array.isArray(res) ? res : []);
    logs.value = items.map((r, idx) => ({ _rowKey: idx, ...r }));
    message.success('慢日志已获取');
  } catch (e) {
    logs.value = [];
  } finally {
    loading.value = false;
  }
}

async function analyzeSlowlog() {
  if (!selectedInstance.value) { message.warning('请选择实例'); return; }
  try {
    loading.value = true;
    const res = await apiClient.analyzeSlowlog(Number(selectedInstance.value));
    analysis.value = res;
    message.success('慢日志分析完成');
  } catch (e) {
    analysis.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => { loadInstances(); });
</script>

<style scoped>
</style>
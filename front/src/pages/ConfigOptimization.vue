<template>
  <a-card title="配置优化" :loading="loading">
    <a-space direction="vertical" style="width:100%">
      <a-space>
        <a-select v-model:value="selectedInstance" style="min-width: 280px" placeholder="选择实例">
          <a-select-option v-for="opt in instanceOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </a-select-option>
        </a-select>
        <a-button @click="loadSummary" :disabled="!selectedInstance">获取指标摘要</a-button>
        <a-button type="primary" @click="loadAdvice" :disabled="!selectedInstance">获取优化建议</a-button>
      </a-space>

      <a-card v-if="summary" title="指标摘要" style="margin-top: 12px">
        <pre style="white-space: pre-wrap">{{ pretty(summary) }}</pre>
      </a-card>
      <a-card v-if="advice" title="优化建议" style="margin-top: 12px">
        <pre style="white-space: pre-wrap">{{ pretty(advice) }}</pre>
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
const summary = ref(null);
const advice = ref(null);

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

async function loadSummary() {
  if (!selectedInstance.value) { message.warning('请选择实例'); return; }
  try {
    loading.value = true;
    summary.value = await apiClient.getMetricsSummary(Number(selectedInstance.value));
    message.success('指标摘要已获取');
  } catch (e) {
    summary.value = null;
  } finally { loading.value = false; }
}

async function loadAdvice() {
  if (!selectedInstance.value) { message.warning('请选择实例'); return; }
  try {
    loading.value = true;
    advice.value = await apiClient.getMetricsAdvice(Number(selectedInstance.value));
    message.success('优化建议已获取');
  } catch (e) {
    advice.value = null;
  } finally { loading.value = false; }
}

onMounted(() => { loadInstances(); });
</script>

<style scoped>
</style>
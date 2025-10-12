<template>
  <a-card title="架构优化" :loading="loading">
    <a-space direction="vertical" style="width:100%">
      <a-space>
        <a-select v-model:value="selectedInstance" style="min-width: 280px" placeholder="选择实例">
          <a-select-option v-for="opt in instanceOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </a-select-option>
        </a-select>
        <a-button type="primary" @click="startAnalyze" :disabled="!selectedInstance">开始架构检查</a-button>
      </a-space>

      <a-card v-if="result" title="分析结果" style="margin-top: 12px">
        <div v-if="result.llmAdvice" style="margin-bottom: 12px">
          <b>AI 建议：</b>
          <div style="white-space: pre-wrap">{{ result.llmAdvice }}</div>
        </div>
        <div v-if="Array.isArray(result.risks) && result.risks.length">
          <b>风险项：</b>
          <ul>
            <li v-for="(r, idx) in result.risks" :key="idx">{{ r }}</li>
          </ul>
        </div>
        <div v-else>
          <pre style="white-space: pre-wrap">{{ pretty(result) }}</pre>
        </div>
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
const result = ref(null);

function pretty(obj) {
  try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
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

async function startAnalyze() {
  if (!selectedInstance.value) { message.warning('请选择实例'); return; }
  try {
    loading.value = true;
    const res = await apiClient.analyzeArchitecture(Number(selectedInstance.value));
    result.value = res;
    message.success('架构检查完成');
  } catch (e) {
    result.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadInstances();
});
</script>

<style scoped>
</style>
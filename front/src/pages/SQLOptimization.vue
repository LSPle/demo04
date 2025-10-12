<template>
  <div class="sql-optimization-container">
    <!-- 页面标题区 -->
    <div class="page-header">
      <h2 class="page-title">SQL审核优化</h2>
      <p class="page-desc">对数据库性能进行分析，并提供优化建议</p>
    </div>

    <!-- 表单区域 -->
    <div class="form-container">
      <div class="form-item">
        <label class="form-label">目标数据库</label>
        <div class="form-selects">
          <a-select 
            v-model:value="selectedInstance" 
            placeholder="选择实例" 
            @change="handleInstanceChange"
            class="instance-select"
          >
            <a-select-option v-for="opt in instanceOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-select-option>
          </a-select>
        </div>
        <!-- 数据库下拉：仅在选择实例后显示 -->
        <transition name="slide-down">
          <div v-if="selectedInstance" class="database-dropdown">
            <div class="database-label">选择数据库</div>
            <a-select 
              v-model:value="selectedDatabase" 
              placeholder="选择数据库"
              class="database-select"
            >
              <a-select-option v-for="opt in databaseOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </div>
        </transition>
      </div>

      <div class="form-item">
        <label class="form-label">SQL 语句</label>
        <a-textarea 
          v-model:value="sqlQuery" 
          :rows="8" 
          placeholder="请输入需要分析的 SQL 语句"
          class="sql-textarea"
        />
      </div>

      <div class="form-actions">
        <a-button type="primary" @click="executeSqlAnalysis" :loading="isAnalyzing" class="analyze-btn">
          开始分析
        </a-button>
        <a-button @click="resetForm" class="reset-btn">
          重置
        </a-button>
      </div>
    </div>

    <!-- 结果展示区域 -->
    <div v-if="optimizationResults" class="results-container">
      <h3 class="results-title">分析结果</h3>
      <div class="results-content">
        <pre>{{ optimizationResults }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';

const selectedInstance = ref('');
const selectedDatabase = ref('');
const sqlQuery = ref('');
const optimizationResults = ref('');
const isAnalyzing = ref(false);

const instanceOptions = ref([]);
const databaseOptions = ref([]);


async function getInstanceList() {
  try {
    const data = await apiClient.getInstances();
    console.log('原始数据:', data);
    
    let list = [];
    if (Array.isArray(data)) {
      list = data;
    } else if (data && Array.isArray(data.instances)) {
      list = data.instances;
    }
    
    // 过滤运行中的实例并格式化选项
    instanceOptions.value = list.filter(i => i.status === 'running').map(i => ({
      value: String(i.id),
      label: `${i.instanceName} (${i.dbType}) ${i.host}:${i.port}`
    }));
  } catch (e) {
    instanceOptions.value = [];
  }
}

async function getDatabaseList(instanceId) {
  try {
    const data = await apiClient.getInstanceDatabases(instanceId);
    databaseOptions.value = (data?.databases || []).map(db => ({ label: db, value: db }));
  } catch (e) {
    databaseOptions.value = [];
    message.error('获取数据库列表失败');
  }
}

function handleInstanceChange(val) {
  selectedDatabase.value = '';
  if (val) getDatabaseList(val);
}

async function executeSqlAnalysis() {
  if (!selectedInstance.value) {
    message.warning('请选择实例');
    return;
  }
  if (!selectedDatabase.value) {
    message.warning('请选择数据库');
    return;
  }
  if (!sqlQuery.value.trim()) {
    message.warning('请输入SQL语句');
    return;
  }
  try {
    isAnalyzing.value = true;
    const res = await apiClient.analyzeSql({
      instanceId: Number(selectedInstance.value),
      database: selectedDatabase.value,
      sql: sqlQuery.value.trim()
    });
    optimizationResults.value = res?.analysis || res?.content || JSON.stringify(res, null, 2);
  } catch (e) {
    message.error(e.message || '分析失败');
  } finally {
    isAnalyzing.value = false;
  }
}

function resetForm() {
  selectedInstance.value = '';
  selectedDatabase.value = '';
  sqlQuery.value = '';
  optimizationResults.value = '';
}

onMounted(() => {
  getInstanceList();
});
</script>

<style scoped>
.sql-optimization-container {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 24px;
}

.page-header {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1a1a1a;
}

.page-desc {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.form-container {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  margin-bottom: 24px;
}

.form-item {
  margin-bottom: 24px;
}

.form-item:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 16px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-selects {
  display: flex;
  gap: 16px;
}

.instance-select {
  flex: 2;
  min-width: 280px;
}

.database-select {
  min-width: 200px;
  font-size: 16px;
}

.instance-select :deep(.ant-select-selector),
.database-select :deep(.ant-select-selector) {
  height: 48px !important;
  border-radius: 12px !important;
  border: 1px solid #d9d9d9 !important;
  padding: 0 16px !important;
}

.instance-select :deep(.ant-select-selection-item),
.database-select :deep(.ant-select-selection-item) {
  line-height: 46px !important;
}

.sql-textarea {
  border-radius: 12px;
  border: 1px solid #d9d9d9;
  padding: 16px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  resize: vertical;
}

.sql-textarea :deep(.ant-input) {
  border: none;
  padding: 0;
  font-family: 'Courier New', monospace;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 32px;
}

.analyze-btn {
  background: #1890ff;
  border-color: #1890ff;
  border-radius: 8px;
  height: 40px;
  padding: 0 24px;
  font-weight: 500;
}

.analyze-btn:hover {
  background: #40a9ff;
  border-color: #40a9ff;
}

.reset-btn {
  border-radius: 8px;
  height: 40px;
  padding: 0 24px;
  font-weight: 500;
}

.results-container {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
}

.results-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: #1a1a1a;
}

.results-content {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e9ecef;
}

.results-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #333;
}

/* 下拉动画与从属关系样式 */
.database-dropdown-wrapper {
  overflow: hidden;
  margin-top: 12px;
  padding: 12px 12px 16px 16px;
  background: rgba(248, 249, 250, 0.9);
  border: 1px solid #e9ecef;
  border-radius: 10px;
  position: relative;
}

.database-dropdown-wrapper::before {
  content: '';
  position: absolute;
  top: -10px;
  left: 16px;
  width: 16px;
  height: 16px;
  background: rgba(248, 249, 250, 0.9);
  border-left: 2px solid #1890ff;
  border-top: 2px solid #1890ff;
  transform: rotate(45deg);
  border-radius: 3px;
}

.sub-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #555;
  font-size: 13px;
}

.chevron {
  color: #1890ff;
}

.instance-tag {
  background: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.database-dropdown { margin-top: 12px; }
.database-label { font-size: 13px; color: #555; margin-bottom: 6px; font-weight: 500; }

/* slide-down 过渡动画 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 240ms ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  max-height: 0;
}

.slide-down-enter-to,
.slide-down-leave-from {
  opacity: 1;
  transform: translateY(0);
  max-height: 240px;
}

@media (max-width: 768px) {
  .form-selects {
    flex-direction: column;
  }
  
  .instance-select,
  .database-select {
    min-width: auto;
  }
}
</style>
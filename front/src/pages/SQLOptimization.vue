<template>
  <div class="sql-optimization-container">
    <!-- 页面标题区 -->
    <div class="config-header">
      <h2 class="config-title">SQL审核优化</h2>
      <p class="config-desc">对数据库性能进行分析，并提供优化建议</p>
    </div>

    <!-- 控制区（与配置优化一致的布局） -->
    <div class="control-section">
      <a-card title="实例选择" class="control-card">
        <a-space direction="vertical" style="width: 100%">
          <!-- 实例选择器 -->
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

          <!-- SQL 输入区 -->
          <div>
            <label class="form-label">SQL 语句</label>
            <a-textarea 
              v-model:value="sqlQuery" 
              :rows="8" 
              placeholder="请输入需要分析的 SQL 语句"
              class="sql-textarea"
            />
          </div>

          <!-- 操作按钮 -->
          <a-space>
            <a-button type="primary" @click="executeSqlAnalysis" :loading="isAnalyzing" class="start-analysis-btn">
              开始分析
            </a-button>
            <a-button @click="resetForm" class="reset-btn">
              重置
            </a-button>
          </a-space>
        </a-space>
      </a-card>
    </div>

    <!-- 数据展示卡片（与配置优化一致的布局） -->
    <div class="data-display-section">
      <a-card title="分析结果" class="data-display-card">
        <!-- 等待态：无结果时显示 -->
        <div v-if="!optimizationResults" class="waiting-state">
          <a-empty description="等待分析结果">
            <template #description>
              <span style="color: #999;">请选择实例、数据库并填写SQL后点击“开始分析”</span>
            </template>
          </a-empty>
        </div>

        <!-- 加载完成态：有结果时显示 -->
        <div v-else class="data-loaded-state">
          <div class="results-content">
            <pre>{{ optimizationResults }}</pre>
          </div>
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

const selectedInstance = ref('');
const selectedDatabase = ref('');
const sqlQuery = ref('');
const optimizationResults = ref('');
const isAnalyzing = ref(false);

const instanceOptions = ref([]);
const databaseOptions = ref([]);


// 使用全局状态管理获取运行中的实例
async function getInstanceList() {
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
  } catch (e) {
    instanceOptions.value = [];
    message.error('获取实例列表失败');
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

// 监听全局缓存清理事件
function handleInstancesCacheCleared() {
  instanceOptions.value = [];
  getInstanceList();
}
window.addEventListener('instances-cache-cleared', handleInstancesCacheCleared);

onUnmounted(() => {
  window.removeEventListener('instances-cache-cleared', handleInstancesCacheCleared);
});

onMounted(() => {
  getInstanceList();
});
</script>

<style scoped>
.sql-optimization-container {
  padding: 0;
}

.config-header {
  margin-bottom: 24px;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.config-title {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.config-desc {
  margin: 0;
  font-size: 14px;
  opacity: 0.9;
}

.control-section {
  margin-bottom: 24px;
}

.control-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

.start-analysis-btn {
  min-width: 100px;
}

.reset-btn {
  border-radius: 8px;
  height: 40px;
  padding: 0 24px;
  font-weight: 500;
}


.data-display-section {
  margin-bottom: 24px;
}

.data-display-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

/* 配置优化页面的动画与等待/加载态 */
.waiting-state {
  padding: 40px 0;
  text-align: center;
}

.data-loaded-state {
  animation: fadeInUp 0.6s ease-out;
}

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

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
<template>
  <!-- 页面主容器 -->
  <div class="instance-overview-container">
    <!-- 页面标题区域 -->
    <div class="config-header">
      <div class="header-content">
        <div class="title-area">
          <h2 class="config-title">实例概览</h2>
          <p class="config-desc">数据库实例运行状态总览</p>
        </div>
        <div class="button-area">
          <a-button type="primary" @click="refresh" :loading="refreshing" class="btn-click-anim">
            刷新状态
          </a-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片区域 -->
    <div class="stats">
      <div class="card total">
        <div class="icon">📊</div>
        <div class="number">{{ totalCount }}</div>
        <div class="label">总实例数</div>
      </div>
      <div class="card running">
        <div class="icon">✅</div>
        <div class="number">{{ runningCount }}</div>
        <div class="label">成功数</div>
      </div>
      <div class="card error">
        <div class="icon">⚠️</div>
        <div class="number">{{ errorCount }}</div>
        <div class="label">异常数</div>
      </div>
    </div>

    <!-- 数据表格区域 -->
    <div class="table">
      <a-table 
        :columns="columns" 
        :data-source="instances" 
        rowKey="id" 
        :pagination="pagination"
        :loading="loading"
      >
        <!-- 确保独立逻辑 -->
        <template v-slot:bodyCell="{ column, record }">
          <template v-if="column.key === 'instanceName'">
            <div class="name">
              <span>{{ record.instanceName }}</span>
            </div>
          </template>
          <template v-else-if="column.key === 'address'">
            <span class="address">{{ record.host }}:{{ record.port }}</span>
          </template>
          <template v-else-if="column.key === 'dbType'">
            <span class="dbType">{{ record.dbType?.toUpperCase() || 'MYSQL' }}</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="getStatusColorByOk(statusMap[record.id])">
              {{ getStatusTextByOk(statusMap[record.id]) }}
            </a-tag>
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup>
// 导入Vue相关功能
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import apiClient from '../utils/apiClient';
import { message } from 'ant-design-vue';
import globalInstances from '../utils/globalInstances';

let cacheClearedHandler = null;

// 页面状态
const loading = ref(false);  // 加载状态
const instances = ref([]);   // 实例列表数据
const refreshing = ref(false); // 刷新按钮禁用状态

// 动态状态映射：{ [id]: boolean }
const statusMap = reactive({});

// 表格列配置
const columns = [
  { title: '实例名称', key: 'instanceName', width: 250 },
  { title: '连接地址', key: 'address', width: 200 },
  { title: '数据库类型', key: 'dbType', width: 120 },
  { title: '状态', key: 'status', width: 100 },
];

// 分页配置
const pagination = computed(() => ({
  pageSize: 10,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total, range) => `共 ${total} 条记录`,
}));

// 统计数据（基于实时检测返回）
const totalCount = ref(0);
const runningCount = ref(0);
const errorCount = ref(0);

// 状态颜色/文本（按连接结果）
function getStatusColorByOk(ok) {
  if (ok === true) return 'green';
  if (ok === false) return 'red';
  return 'default';
}
function getStatusTextByOk(ok) {
  if (ok === true) return '运行中';
  if (ok === false) return '异常';
  return '未知';
}

// 使用全局状态管理加载实例数据
async function loadInstancesData(showMessage = false) {
  try {
    loading.value = true;
    const success = await globalInstances.loadInstances(showMessage);
    
    if (success) {
      // 从全局状态获取数据
      instances.value = globalInstances.getAllInstances();
      const globalStatusMap = globalInstances.getStatusMap();
      
      // 更新本地状态映射
      Object.keys(statusMap).forEach(k => delete statusMap[k]);
      Object.assign(statusMap, globalStatusMap);
      
      // 计算统计数据
      const allInstances = globalInstances.getAllInstances();
      const runningInstances = globalInstances.getRunningInstances();
      
      totalCount.value = allInstances.length;
      runningCount.value = runningInstances.length;
      errorCount.value = allInstances.length - runningInstances.length;
      
      if (showMessage) message.success('数据加载成功');
    }
  } catch (error) {
    instances.value = [];
    totalCount.value = 0;
    runningCount.value = 0;
    errorCount.value = 0;
    if (showMessage) message.error(error.message || '加载数据失败');
  } finally {
    loading.value = false;
  }
}

// 刷新按钮
async function refresh() {
  try {
    refreshing.value = true;
    // 清空全局缓存并通知其他页面，同时本页立即重新加载
    globalInstances.clearGlobalData();
    await loadInstancesData(true);
  } catch (e) {
    message.error('刷新失败');
  } finally {
    refreshing.value = false;
  }
}

onMounted(async () => {
  await loadInstancesData(false);
  cacheClearedHandler = () => {
    loadInstancesData(false);
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
/* 实例概览页面样式 */
.instance-overview-container {
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

.button-area {
  display: flex;
  gap: 12px;
}

/* 统计卡片区域 */
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.card {
  background: rgba(255, 255, 255, 0.95);
  padding: 20px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s ease;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.card .icon {
  font-size: 24px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(24, 144, 255, 0.1);
}

.card .number {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1;
}

.card .label {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.card.total .icon {
  background: rgba(24, 144, 255, 0.1);
}

.card.running .icon {
  background: rgba(82, 196, 26, 0.1);
}

.card.error .icon {
  background: rgba(255, 77, 79, 0.1);
}

/* 数据表格区域 */
.table {
  background: rgba(255, 255, 255, 0.95);
  padding: 24px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 表格内容样式 */
.name {
  font-weight: 500;
  color: #1a1a1a;
}

.address {
  font-family: 'Courier New', monospace;
  color: #666;
  font-size: 13px;
}

.dbType {
  font-weight: 500;
  color: #1890ff;
  display: inline-block;
  width: 100%;
  text-align: center;
}

/* 表头（列名）居中 */
.table :deep(.ant-table-thead > tr > th) {
  text-align: center;
}

/* 表体（单元格）居中 */
.table :deep(.ant-table-tbody > tr > td) {
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

.stats,
.table {
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
  
  .stats {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }
  
  .card {
    padding: 16px;
  }
  
  .card .number {
    font-size: 24px;
  }
  
  .table {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .config-header {
    padding: 12px;
  }
  
  .config-title {
    font-size: 18px;
  }
  
  .card {
    padding: 12px;
    gap: 12px;
  }
  
  .card .icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }
  
  .card .number {
    font-size: 20px;
  }
  
  .table {
    padding: 12px;
  }
}
</style>

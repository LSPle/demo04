<template>
  <!-- 页面主容器 -->
  <div class="container">
    <!-- 页面标题区域 -->
    <div class="header">
      <div class="header-content">
        <div class="title-area">
          <h2 class="title">实例概览</h2>
          <p class="desc">数据库实例运行状态总览</p>
        </div>
        <div class="button-area">
          <a-button type="primary" @click="refresh" :loading="loading">
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
        <div class="label">运行中</div>
      </div>
      <div class="card error">
        <div class="icon">⚠️</div>
        <div class="number">{{ errorCount }}</div>
        <div class="label">异常/关闭</div>
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
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup>
// 导入Vue相关功能
import { ref, computed, onMounted } from 'vue';
import apiClient from '../utils/apiClient';
import { message } from 'ant-design-vue';

// 页面状态
const loading = ref(false);  // 加载状态
const instances = ref([]);   // 实例列表数据

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

// 统计数据
const totalCount = computed(() => instances.value.length);
const runningCount = computed(() => instances.value.filter(item => item.status === 'running').length);
const errorCount = computed(() => instances.value.filter(item => item.status === 'error' || item.status === 'closed').length);

// 获取状态颜色
function getStatusColor(status) {
  if (status === 'running') return 'green';
  if (status === 'error' || status === 'closed') return 'red';
  return 'default';
}

// 获取状态文本
function getStatusText(status) {
  if (status === 'running') return '运行中';
  if (status === 'error') return '异常';
  if (status === 'closed') return '已关闭';
  return '未知';
}

// 获取实例数据
async function getInstances(showMessage = false) {
  try {
    loading.value = true;
    const data = await apiClient.getInstances();
    instances.value = Array.isArray(data) ? data : (Array.isArray(data?.instances) ? data.instances : []);
    if (showMessage) message.success('刷新成功');
  } catch (error) {
    instances.value = [];
    if (showMessage) message.error(error.message || '获取实例失败');
  } finally {
    loading.value = false;
  }
  //查看实例数据
  console.log("实例数据:", instances.value);
  
}

// 刷新数据
function refresh() {
  getInstances(true);
}

// 页面加载时获取数据
onMounted(() => {
  getInstances(false);
});
</script>

<style scoped>
/* 页面主容器 */
.container {
  /* background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); */
  min-height: 100vh;
  padding: 24px;
}

/* 页面标题区域 */
.header {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-area {
  flex: 1;
}

.title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1a1a1a;
}

.desc {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.button-area {
  flex-shrink: 0;
}

/* 统计卡片区域 */
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px 20px;
  text-align: center;
  transition: transform 0.2s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card:hover {
  transform: translateY(-2px);
}

.icon {
  font-size: 28px;
  margin-bottom: 12px;
  display: block;
}

.number {
  font-size: 40px;
  font-weight: 700;
  margin-bottom: 6px;
}

/* 不同类型卡片的数字颜色 */
.total .number {
  color: #667eea;
}

.running .number {
  color: #4ade80;
}

.error .number {
  color: #f87171;
}

.label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

/* 数据表格区域 */
.table {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px;
}

/* 表格样式 */
.table :deep(.ant-table) {
  background: transparent;
}

.table :deep(.ant-table-thead > tr > th) {
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  font-weight: 600;
  color: #333;
}

.table :deep(.ant-table-tbody > tr > td) {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 12px;
}

.table :deep(.ant-table-tbody > tr:hover > td) {
  background: #f8f9ff;
}

/* 实例名称样式 */
.name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  margin-left: 10px;
}

.name-icon {
  font-size: 14px;
}

/* 地址样式 */
.address {
  color: #666;
  font-family: 'Courier New', monospace;
  font-size: 16px;
}

.table .dbType{
  color: #666;
  font-size: 16px;
  margin-left: 10px;
}
</style>
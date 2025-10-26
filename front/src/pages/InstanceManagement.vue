<template>
  <div class="management-container">
    <!-- 顶部操作栏 -->
    <div class="config-header">
      <div class="header-content">
        <div class="title-area">
          <h2 class="config-title">实例管理</h2>
          <p class="config-desc">添加、编辑、删除数据库实例，支持实时状态检测</p>
        </div>
        <div class="button-area">
          <a-space>
            <a-button type="primary" @click="showAddDialog" class="btn-click-anim">新增实例</a-button>
            <a-button @click="refresh" :loading="refreshing" class="btn-click-anim">刷新状态</a-button>
          </a-space>
        </div>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-container">
      <a-table :columns="columns" :data-source="instances" :loading="loading" rowKey="id">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'instanceName'">
            <div style="display: flex; align-items: center; justify-content: center; gap: 6px;">
              <span>{{ record.instanceName }}</span>
            </div>
          </template>
          <template v-else-if="column.key === 'dbType'">
            <span class="dbType">{{ (record.dbType || 'MYSQL').toUpperCase() }}</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="getStatusColorByOk(statusMap[record.id])" class="status-tag">
              {{ getStatusTextByOk(statusMap[record.id]) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'createTime'">
            <span class="create-time">{{ formatDateTime(record.createTime) }}</span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space>
              <a-button size="small" type="link" @click="showEditDialog(record)" class="edit-btn btn-click-anim">编辑</a-button>
              <a-popconfirm 
                title="确认删除该实例？" 
                ok-text="删除" 
                cancel-text="取消" 
                @confirm="() => deleteInstanceData(record.id)"
              >
                <a-button size="small" type="link" danger class="delete-btn btn-click-anim">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <a-modal 
      :open="formVisible" 
      :title="isEdit ? '编辑实例' : '新增实例'" 
      @ok="saveInstanceData" 
      @cancel="hideDialog" 
      destroyOnClose
      width="500px"
      class="instance-modal"
    >
      <a-form layout="vertical" class="instance-form">
        <a-form-item label="实例名称" required>
          <a-input 
            v-model:value="form.instanceName" 
            placeholder="例如：生产库" 
            size="large"
          />
        </a-form-item>
        <a-form-item label="数据库类型" required>
          <a-select 
            v-model:value="form.dbType" 
            placeholder="选择类型"
            size="large"
          >
            <a-select-option value="mysql">MySQL</a-select-option>
            <a-select-option value="postgresql" disabled>PostgreSQL</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="主机" required>
          <a-input 
            v-model:value="form.host" 
            placeholder="127.0.0.1" 
            size="large"
          />
        </a-form-item>
        <a-form-item label="端口" required>
          <a-input-number 
            v-model:value="form.port" 
            :min="1" 
            :max="65535" 
            style="width: 100%" 
            size="large"
          />
        </a-form-item>
        <a-form-item label="用户名" required>
          <a-input 
            v-model:value="form.username" 
            placeholder="root" 
            size="large"
          />
        </a-form-item>
        <a-form-item label="密码" required>
          <a-input-password 
            v-model:value="form.password" 
            placeholder="******" 
            size="large"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';
import globalInstances from '../utils/globalInstances';

let cacheClearedHandler = null;

const loading = ref(false);
const instances = ref([]);
const refreshing = ref(false); // 刷新按钮禁用状态

// 动态状态映射（id -> ok）
const statusMap = reactive({});

const columns = [
  { title: '实例名称', key: 'instanceName', width: 300 },
  { title: '数据库类型', key: 'dbType', width: 120 },
  { title: '状态', key: 'status', width: 100 },
  { title: '创建时间', key: 'createTime', width: 180 },
  { title: '操作', key: 'actions', width: 120 },
];

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

function formatDateTime(time) {
  if (!time) return '-';
  try {
    const val = typeof time === 'string' ? time.replace(' ', 'T') : time;
    const d = new Date(val);
    if (isNaN(d.getTime())) return String(time);
    return d.toLocaleString('zh-CN');
  } catch {
    return String(time);
  }
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
      
      if (showMessage) message.success('数据加载成功');
    }
  } catch (error) {
    instances.value = [];
    if (showMessage) message.error(error.message || '加载数据失败');
  } finally {
    loading.value = false;
  }
}

async function refresh() {
  try {
    refreshing.value = true;
    // 直接重新加载数据，避免触发全局清理导致的并发加载
    await loadInstancesData(true);
  } catch (e) {
    message.error('刷新失败');
  } finally {
    refreshing.value = false;
  }
}

// 弹窗部分保持不变
const formVisible = ref(false);
const isEdit = ref(false);
const currentId = ref(null);
const form = reactive({
  instanceName: '',
  dbType: 'mysql',
  host: '',
  port: 3306,
  username: '',
  password: ''
});

function showAddDialog() {
  isEdit.value = false;
  currentId.value = null;
  form.instanceName = '';
  form.dbType = 'mysql';
  form.host = '';
  form.port = 3306;
  form.username = '';
  form.password = '';
  formVisible.value = true;
}

function showEditDialog(record) {
  isEdit.value = true;
  currentId.value = record.id;
  form.instanceName = record.instanceName || '';
  form.dbType = (record.dbType || 'mysql').toLowerCase();
  form.host = record.host || '';
  form.port = record.port || 3306;
  form.username = record.username || '';
  form.password = record.password || '';
  formVisible.value = true;
}

function hideDialog() {
  formVisible.value = false;
}

async function saveInstanceData() {
  if (!form.instanceName || !form.host || !form.port || !form.username || !form.password) {
    message.warning('请完整填写表单');
    return;
  }
  try {
    loading.value = true;
    // 修复字段名映射：前端使用instanceName，后端期望name
    // 修复数据库类型大小写：前端使用mysql，后端期望MySQL
    const payload = {
      name: form.instanceName,  // 映射字段名
      host: form.host,
      port: form.port,
      username: form.username,
      password: form.password,
      type: form.dbType === 'mysql' ? 'MySQL' : form.dbType  // 修复大小写
    };
    if (isEdit.value && currentId.value != null) {
      await apiClient.updateInstance(currentId.value, payload);
      message.success('实例已更新');
    } else {
      await apiClient.createInstance(payload);
      message.success('实例已创建');
    }
    
    // 清除全局缓存，确保其他页面能获取到最新数据
    globalInstances.clearGlobalData();
    
    formVisible.value = false;
    await loadInstancesData(false);
  } catch (e) {
    message.error(e.message || '保存失败');
  } finally {
    loading.value = false;
  }
}

async function deleteInstanceData(id) {
  try {
    loading.value = true;
    await apiClient.deleteInstance(id);
    message.success('实例已删除');
    
    // 清除全局缓存，确保其他页面能获取到最新数据
    globalInstances.clearGlobalData();
    
    await loadInstancesData(false);
  } catch (e) {
    message.error(e.message || '删除失败');
  } finally {
    loading.value = false;
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
/* 实例管理页面样式 */
.management-container {
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

/* 表格容器 */
.table-container {
  background: rgba(255, 255, 255, 0.95);
  padding: 24px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 表格内容样式 */
.status-tag { 
  font-weight: 500; 
}

.create-time { 
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

.edit-btn { 
  color: #1890ff;
  font-weight: 500;
}

.delete-btn { 
  color: #ff4d4f;
  font-weight: 500;
}

/* 弹窗样式 */
.instance-modal { 
  max-width: 520px;
}

.instance-form { 
  margin-top: 8px;
}

.instance-form .ant-form-item {
  margin-bottom: 20px;
}

.instance-form .ant-form-item-label {
  font-weight: 500;
  color: #333;
}

.instance-form .ant-input,
.instance-form .ant-input-number,
.instance-form .ant-select-selector {
  border-radius: 8px;
  border: 1px solid #d9d9d9;
  transition: all 0.3s ease;
}

.instance-form .ant-input:focus,
.instance-form .ant-input-number:focus,
.instance-form .ant-select-focused .ant-select-selector {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
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

.table-container {
  animation: fadeInUp 0.6s ease-out;
}

/* 表头（列名）居中 */
.table-container :deep(.ant-table-thead > tr > th) {
  text-align: center;
}

/* 表体（单元格）居中 */
.table-container :deep(.ant-table-tbody > tr > td) {
  text-align: center;
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
  
  .table-container {
    padding: 16px;
  }
  
  .instance-modal {
    max-width: 90vw;
  }
}

@media (max-width: 480px) {
  .config-header {
    padding: 12px;
  }
  
  .config-title {
    font-size: 18px;
  }
  
  .table-container {
    padding: 12px;
  }
  
  .button-area .ant-btn {
    font-size: 12px;
    height: 32px;
    padding: 0 12px;
  }
}
</style>
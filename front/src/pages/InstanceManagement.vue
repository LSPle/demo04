<template>
  <div class="management-container">
    <!-- 页面标题区 -->
    <div class="management-header">
      <h2 class="management-title">实例管理</h2>
      <p class="management-desc">添加、编辑和删除数据库实例</p>
    </div>

    <!-- 操作按钮区 -->
    <div class="action-bar">
      <a-button @click="refresh" class="refresh-btn">
        刷新
      </a-button>
      <a-button type="primary" @click="AddInstance" class="add-btn">
        新增实例
      </a-button>
    </div>

    <!-- 实例列表表格 -->
    <div class="table-container">
      <a-table 
        :columns="columns" 
        :data-source="instances" 
        rowKey="id" 
        :pagination="{ pageSize: 10, showSizeChanger: true, showQuickJumper: true, showTotal: (total, range) => `共 ${total} 条记录` }"
        :loading="loading"
        class="instance-table" >

        <template v-slot:bodyCell="{ column, record }">
          <template v-if="column.key === 'instanceName'">
            <div class="instance-name">
              <div class="name-info">
                <div class="name-text">{{ record.instanceName }}</div>
                <div class="name-detail">{{ record.host }}:{{ record.port }}</div>
              </div>
            </div>
          </template>
          <template v-else-if="column.key === 'dbType'">
            <span class="db-type">{{ record.dbType?.toUpperCase() || 'MYSQL' }}</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)" class="status-tag">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'createTime'">
            <span class="create-time">{{ formatDateTime(record.createTime) }}</span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space>
              <a-button size="small" type="link" @click="showEditDialog(record)" class="edit-btn">编辑</a-button>
              <!-- Ant Design Vue的确认弹窗 -->
              <a-popconfirm 
                title="确认删除该实例？" 
                ok-text="删除" 
                cancel-text="取消" 
                @confirm="() => deleteInstanceData(record.id)"
              >
                <a-button size="small" type="link" danger class="delete-btn">删除</a-button>
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
            <a-select-option value="postgresql">PostgreSQL</a-select-option>
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
import { ref, reactive, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';

const loading = ref(false);
const instances = ref([]);

const columns = [
  { title: '实例名称', key: 'instanceName', width: 300 },
  { title: '数据库类型', key: 'dbType', width: 120 },
  { title: '状态', key: 'status', width: 100 },
  { title: '创建时间', key: 'createTime', width: 180 },
  { title: '操作', key: 'actions', width: 120 },
];

function getStatusColor(status) {
  if (status === 'running') return 'green';
  if (status === 'error' || status === 'closed') return 'red';
  return 'default';
}

function getStatusText(status) {
  if (status === 'running') return '运行中';
  if (status === 'error') return '异常';
  if (status === 'closed') return '已关闭';
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

async function getInstanceList(showMessage = false) {
  try {
    loading.value = true;
    const data = await apiClient.getInstances();
    instances.value = Array.isArray(data) ? data : (Array.isArray(data?.instances) ? data.instances : []);
    if (showMessage) message.success('刷新成功');
  } catch (e) {
    instances.value = [];
    if (showMessage) message.error(e.message || '获取实例失败');
  } finally {
    loading.value = false;
  }
}

function refresh() {
  getInstanceList(true);
}

const formVisible = ref(false);
const isEdit = ref(false);
const currentId = ref(null);
const form = reactive({
  instanceName: '',
  dbType: 'mysql',
  host: '127.0.0.1',
  port: 3306,
  username: '',
  password: ''
});

//重置表单数据
function clearFormData() {
  form.instanceName = '';
  form.dbType = 'mysql';
  form.host = '127.0.0.1';
  form.port = 3306;
  form.username = '';
  form.password = '';
  currentId.value = null;
}

function AddInstance() {
  clearFormData();
  isEdit.value = false;
  formVisible.value = true;
}

function showEditDialog(record) {
  isEdit.value = true;
  currentId.value = record.id;
  form.instanceName = record.instanceName || '';
  form.dbType = record.dbType || 'mysql';
  form.host = record.host || '127.0.0.1';
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
    const payload = { ...form };
    if (isEdit.value && currentId.value != null) {
      await apiClient.updateInstance(currentId.value, payload);
      message.success('实例已更新');
    } else {
      await apiClient.createInstance(payload);
      message.success('实例已创建');
    }
    formVisible.value = false;
    await getInstanceList(false);
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
    await getInstanceList(false);
  } catch (e) {
    message.error(e.message || '删除失败');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  getInstanceList(false);
});
</script>

<style scoped>
.management-container {
  background: none;
  padding: 0;
}

.management-header {
  background: rgba(255, 255, 255, 0.95);
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.management-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1a1a1a;
}

.management-desc {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.action-bar {
  background: rgba(255, 255, 255, 0.95);
  padding: 16px 24px;
  border-radius: 12px;
  margin-bottom: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.refresh-btn, .add-btn {
  border-radius: 8px;
  height: 36px;
  padding: 0 20px;
  font-weight: 500;
}

.refresh-btn {
  margin-right: 12px;
}

.table-container {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.instance-table :deep(.ant-table) {
  background: transparent;
}

.instance-table :deep(.ant-table-thead > tr > th) {
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  font-weight: 600;
  color: #333;
}

.instance-table :deep(.ant-table-tbody > tr > td) {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 12px;
}

.instance-table :deep(.ant-table-tbody > tr:hover > td) {
  background: #f8f9ff;
}

.instance-name {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
}

/* .name-icon {
  font-size: 16px;
} */

.name-info {
  flex: 1;
}

.name-text {
  font-weight: 500;
  color: #1a1a1a;
  margin-bottom: 2px;
}

.name-detail {
  font-size: 12px;
  color: #999;
}

.db-type {
  font-weight: 500;
  color: #333;
}

.status-tag {
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.create-time {
  color: #666;
  font-size: 13px;
}

.edit-btn, .delete-btn {
  padding: 0;
  height: auto;
  font-size: 13px;
}

.instance-modal :deep(.ant-modal-header) {
  border-bottom: 1px solid #f0f0f0;
  padding: 20px 24px;
}

.instance-modal :deep(.ant-modal-title) {
  font-size: 18px;
  font-weight: 600;
}

.instance-form {
  padding-top: 16px;
}

.instance-form :deep(.ant-form-item-label > label) {
  font-weight: 500;
  color: #333;
}

.instance-form :deep(.ant-input),
.instance-form :deep(.ant-select-selector),
.instance-form :deep(.ant-input-number) {
  border-radius: 6px;
}

.db-type {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.create-time {
  font-size: 16px;
  color: #666;
  font-weight: 400;
}
</style>
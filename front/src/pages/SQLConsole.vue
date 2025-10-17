<template>
  <div class="sql-console-container">
    <!-- 标题区：与配置优化页面一致 -->
    <div class="config-header">
      <div class="config-title">SQL窗口</div>
      <div class="config-desc">查询数据库、执行SQL并查看历史记录</div>
    </div>

    <!-- 控制区：左右卡片布局 -->
    <div class="control-section">
      <a-row :gutter="16">
        <!-- 左侧：实例选择 + 数据库树 -->
        <a-col :xs="24" :md="8">
          <a-card class="control-card">
            <template #title>
              <div class="card-title">数据库/表结构</div>
            </template>
            <template #extra>
              <a-button size="small" @click="handleRefreshDatabases" :loading="loadingDatabases" class="refresh-db-btn">
                刷新
              </a-button>
            </template>

            <div class="instance-selector">
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

            <div class="sidebar-content">
              <div v-if="!selectedInstance" class="empty-state">
                <div class="empty-icon">📁</div>
                <div class="empty-text">请先选择实例</div>
              </div>
              <div v-else-if="loadingDatabases" class="loading-state">
                <a-spin size="small" />
                <span>加载中...</span>
              </div>
              <div v-else class="database-tree">
                <div v-for="database in databaseList" :key="database.name" class="database-item">
                  <div 
                    class="database-header" 
                    @click="handleToggleDatabase(database.name)"
                    :class="{ expanded: expandedDatabases.includes(database.name) }"
                  >
                    <span class="expand-icon">
                      {{ expandedDatabases.includes(database.name) ? '📂' : '📁' }}
                    </span>
                    <span class="database-name">{{ database.name }}</span>
                  </div>
                  <div v-if="expandedDatabases.includes(database.name)" class="table-list">
                    <div v-if="database.loading" class="table-loading">
                      <a-spin size="small" />
                      <span>加载表结构...</span>
                    </div>
                    <div v-else-if="database.tables?.length" class="tables">
                      <div 
                        v-for="table in database.tables" 
                        :key="table.name" 
                        class="table-item"
                        @click="handleSelectTable(database.name, table.name)"
                        :class="{ active: selectedTable === `${database.name}.${table.name}` }"
                      >
                        <span class="table-icon">📋</span>
                        <span class="table-name">{{ table.name }}</span>
                        <span class="table-type">{{ table.type || '表' }}</span>
                      </div>
                    </div>
                    <div v-else class="no-tables">
                      <span>暂无表</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </a-card>
        </a-col>

        <!-- 右侧：SQL编辑器 -->
        <a-col :xs="24" :md="16">
          <a-card class="control-card">
            <template #title>
              <div class="card-title">SQL编辑器</div>
            </template>
            <div class="editor-section">
              <div class="editor-header">
                <div class="editor-actions">
                  <a-select 
                    v-model:value="selectedDatabase" 
                    placeholder="选择数据库"
                    class="database-select"
                    size="small"
                  >
                    <a-select-option v-for="db in databaseList" :key="db.name" :value="db.name">
                      {{ db.name }}
                    </a-select-option>
                  </a-select>
                  <a-button @click="resetForm" class="reset-btn" size="small">重置</a-button>
                  <a-button type="primary" @click="executeSql" :loading="loading" size="small" class="execute-btn">
                    执行SQL
                  </a-button>
                </div>
              </div>
              <div class="editor-content">
                <a-textarea 
                  v-model:value="sql" 
                  :rows="12" 
                  placeholder="请输入SQL语句..."
                  class="sql-editor"
                />
              </div>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </div>

    <!-- 数据展示区：与配置优化页面一致 -->
    <div class="data-display-section">
      <a-card class="data-display-card">
        <div class="results-tabs">
          <div 
            class="tab-item" 
            :class="{ active: activeTab === 'result' }"
            @click="activeTab = 'result'"
          >
            执行结果
          </div>
          <div 
            class="tab-item" 
            :class="{ active: activeTab === 'history' }"
            @click="activeTab = 'history'"
          >
            执行历史
          </div>
        </div>
        <div class="results-content">
          <div v-if="activeTab === 'result'" class="result-panel">
            <div v-if="!result" class="empty-result">
              <div class="empty-icon">📊</div>
              <div class="empty-text">暂无执行结果</div>
            </div>
            <div v-else class="result-data">
              <div v-if="resultTable.columns.length" class="table-result">
                <a-table 
                  :columns="resultTable.columns" 
                  :data-source="resultTable.rows" 
                  :pagination="{ pageSize: 50, showSizeChanger: true }"
                  rowKey="_rowKey" 
                  size="small"
                  class="result-table"
                />
              </div>
              <div v-else class="text-result">
                <pre>{{ pretty(result) }}</pre>
              </div>
            </div>
          </div>
          <div v-if="activeTab === 'history'" class="history-panel">
            <div v-if="!executionHistory.length" class="empty-result">
              <div class="empty-icon">📝</div>
              <div class="empty-text">暂无执行历史</div>
            </div>
            <div v-else class="history-list">
              <div class="history-header">
                <span class="history-count">共 {{ executionHistory.length }} 条记录</span>
                <a-button size="small" @click="clearHistory" class="clear-btn">清空历史</a-button>
              </div>
              <div class="history-items">
                <div 
                  v-for="item in executionHistory" 
                  :key="item.id" 
                  class="history-item"
                  :class="{ 'error': !item.success }"
                >
                  <div class="history-item-header">
                    <div class="history-meta">
                      <span class="history-time">{{ formatTime(item.timestamp) }}</span>
                      <span class="history-database">{{ item.database }}</span>
                      <span class="history-status" :class="item.success ? 'success' : 'error'">
                        {{ item.success ? '成功' : '失败' }}
                      </span>
                      <span v-if="item.duration" class="history-duration">{{ item.duration }}ms</span>
                    </div>
                    <div class="history-actions">
                      <a-button size="small" @click="rerunSql(item)" class="rerun-btn">重新执行</a-button>
                      <a-button size="small" @click="deleteSingleHistory(item.id)" class="delete-btn">删除</a-button>
                    </div>
                  </div>
                  <div class="history-sql">
                    <pre>{{ item.sql }}</pre>
                  </div>
                  <div v-if="item.error" class="history-error">
                    <span class="error-label">错误信息：</span>
                    <span class="error-message">{{ item.error }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';

const loading = ref(false);
const loadingDatabases = ref(false);
const instanceOptions = ref([]);
const databaseList = ref([]);
const selectedInstance = ref('');
const selectedDatabase = ref('');
const selectedTable = ref('');
const expandedDatabases = ref([]);
const sql = ref('');
const result = ref(null);
const resultTable = ref({ columns: [], rows: [] });
const activeTab = ref('result');

// 执行历史相关状态
const executionHistory = ref([]);
const maxHistorySize = 50; // 最大历史记录数量

function pretty(obj) {
  try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
}

async function getInstanceList() {
  try {
    const data = await apiClient.getInstances();
    const list = Array.isArray(data) ? data : (Array.isArray(data?.instances) ? data.instances : []);
    instanceOptions.value = list.filter(i => i.status === 'running').map(i => ({
      value: String(i.id),
      label: `${i.instanceName} (${i.dbType}) ${i.host}:${i.port}`
    }));
  } catch (e) {
    instanceOptions.value = [];
  }
}

async function getDatabaseList(instanceId) {
  if (!instanceId) return;
  try {
    loadingDatabases.value = true;
    const data = await apiClient.getInstanceDatabases(instanceId);
    const databases = data?.databases || [];
    databaseList.value = databases.map(db => ({
      name: db,
      tables: [],
      loading: false
    }));
  } catch (e) {
    databaseList.value = [];
    message.error('获取数据库列表失败');
  } finally {
    loadingDatabases.value = false;
  }
}

async function getTableList(databaseName) {
  if (!selectedInstance.value || !databaseName) return;
  
  const database = databaseList.value.find(db => db.name === databaseName);
  if (!database) return;
  
  try {
    database.loading = true;
    // 调用后端API获取该数据库的表列表
    const res = await apiClient.getDatabaseTables(Number(selectedInstance.value), databaseName);
    const tables = Array.isArray(res?.tables) ? res.tables : (Array.isArray(res) ? res : []);
    database.tables = tables.map(t => {
      if (typeof t === 'string') return { name: t, type: '表' };
      return { name: t?.name ?? String(t), type: t?.type ?? '表' };
    });
  } catch (e) {
    database.tables = [];
    message.error('获取表结构失败');
  } finally {
    database.loading = false;
  }
}

function handleInstanceChange(val) {
  selectedDatabase.value = '';
  selectedTable.value = '';
  expandedDatabases.value = [];
  if (val) getDatabaseList(val);
}

function handleRefreshDatabases() {
  if (selectedInstance.value) {
    getDatabaseList(selectedInstance.value);
  }
}

function handleToggleDatabase(databaseName) {
  const index = expandedDatabases.value.indexOf(databaseName);
  if (index > -1) {
    expandedDatabases.value.splice(index, 1);
  } else {
    expandedDatabases.value.push(databaseName);
    getTableList(databaseName);
  }
}

function handleSelectTable(databaseName, tableName) {
  selectedTable.value = `${databaseName}.${tableName}`;
  selectedDatabase.value = databaseName;
  // 自动生成查询语句
  sql.value = `SELECT * FROM ${tableName} LIMIT 100;`;
}

function resetForm() {
  selectedInstance.value = '';
  selectedDatabase.value = '';
  selectedTable.value = '';
  expandedDatabases.value = [];
  sql.value = '';
  result.value = null;
  resultTable.value = { columns: [], rows: [] };
  databaseList.value = [];
}

function toTable(res) {
  const rows = Array.isArray(res?.rows) ? res.rows : (Array.isArray(res?.data) ? res.data : []);
  if (!rows.length) return { columns: [], rows: [] };

  const sample = rows[0];
  const keys = Array.isArray(res?.columns) && res.columns.length ? res.columns : Object.keys(sample);
  const columns = keys.map(k => ({ title: String(k), dataIndex: String(k), key: String(k) }));
  const withKey = rows.map((r, idx) => ({ _rowKey: idx, ...r }));
  return { columns, rows: withKey };
}

// 添加历史记录的函数
function addToHistory(sqlText, result, error = null) {
  const historyItem = {
    id: Date.now() + Math.random(), // 简单的唯一ID
    sql: sqlText,
    database: selectedDatabase.value,
    instance: selectedInstance.value,
    instanceName: instanceOptions.value.find(opt => opt.value === selectedInstance.value)?.label || '',
    timestamp: new Date(),
    success: !error,
    result: error ? null : result,
    error: error,
    duration: null // 可以后续添加执行时间统计
  };
  
  // 添加到历史记录开头
  executionHistory.value.unshift(historyItem);
  
  // 限制历史记录数量
  if (executionHistory.value.length > maxHistorySize) {
    executionHistory.value = executionHistory.value.slice(0, maxHistorySize);
  }
  
  // 保存到本地存储
  saveHistoryToLocal();
}

// 保存历史记录到本地存储
function saveHistoryToLocal() {
  try {
    localStorage.setItem('sql_execution_history', JSON.stringify(executionHistory.value));
  } catch (e) {
    console.warn('无法保存历史记录到本地存储:', e);
  }
}

// 从本地存储加载历史记录
function loadHistoryFromLocal() {
  try {
    const saved = localStorage.getItem('sql_execution_history');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        executionHistory.value = parsed.map(item => ({
          ...item,
          timestamp: new Date(item.timestamp) // 确保时间戳是Date对象
        }));
      }
    }
  } catch (e) {
    console.warn('无法从本地存储加载历史记录:', e);
    executionHistory.value = [];
  }
}

async function executeSql() {
  if (!selectedInstance.value) { message.warning('请选择实例'); return; }
  if (!selectedDatabase.value) { message.warning('请选择数据库'); return; }
  if (!sql.value.trim()) { message.warning('请输入 SQL'); return; }
  
  const sqlText = sql.value.trim();
  const startTime = Date.now();
  
  try {
    loading.value = true;
    const res = await apiClient.executeSql({
      instanceId: Number(selectedInstance.value),
      database: selectedDatabase.value,
      sql: sqlText
    });
    
    const duration = Date.now() - startTime;
    result.value = res;
    resultTable.value = toTable(res);
    activeTab.value = 'result';
    
    // 添加成功的执行记录到历史
    const historyItem = {
      id: Date.now() + Math.random(),
      sql: sqlText,
      database: selectedDatabase.value,
      instance: selectedInstance.value,
      instanceName: instanceOptions.value.find(opt => opt.value === selectedInstance.value)?.label || '',
      timestamp: new Date(),
      success: true,
      result: res,
      error: null,
      duration: duration
    };
    
    executionHistory.value.unshift(historyItem);
    if (executionHistory.value.length > maxHistorySize) {
      executionHistory.value = executionHistory.value.slice(0, maxHistorySize);
    }
    saveHistoryToLocal();
    
    message.success('执行完成');
  } catch (e) {
    const duration = Date.now() - startTime;
    result.value = null;
    resultTable.value = { columns: [], rows: [] };
    
    // 添加失败的执行记录到历史
    const historyItem = {
      id: Date.now() + Math.random(),
      sql: sqlText,
      database: selectedDatabase.value,
      instance: selectedInstance.value,
      instanceName: instanceOptions.value.find(opt => opt.value === selectedInstance.value)?.label || '',
      timestamp: new Date(),
      success: false,
      result: null,
      error: e.message || '执行失败',
      duration: duration
    };
    
    executionHistory.value.unshift(historyItem);
    if (executionHistory.value.length > maxHistorySize) {
      executionHistory.value = executionHistory.value.slice(0, maxHistorySize);
    }
    saveHistoryToLocal();
    
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  getInstanceList();
  loadHistoryFromLocal(); // 加载历史记录
});

// 格式化时间显示
function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  // 如果是今天
  if (diff < 24 * 60 * 60 * 1000 && date.getDate() === now.getDate()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  
  // 如果是昨天或更早
  return date.toLocaleString('zh-CN', { 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit' 
  });
}

// 重新执行SQL
function rerunSql(historyItem) {
  // 设置实例和数据库
  selectedInstance.value = historyItem.instance;
  selectedDatabase.value = historyItem.database;
  
  // 设置SQL内容
  sql.value = historyItem.sql;
  
  // 切换到结果标签页
  activeTab.value = 'result';
  
  // 提示用户
  message.info('已加载历史SQL，点击执行按钮重新运行');
}

// 删除单条历史记录
function deleteSingleHistory(historyId) {
  const index = executionHistory.value.findIndex(item => item.id === historyId);
  if (index > -1) {
    executionHistory.value.splice(index, 1);
    saveHistoryToLocal();
    message.success('已删除历史记录');
  }
}

// 清空所有历史记录
function clearHistory() {
  executionHistory.value = [];
  saveHistoryToLocal();
  message.success('已清空所有历史记录');
}
</script>

<style scoped>
.sql-console-container {
  min-height: 100vh;
  padding: 0;
  display: flex;
  flex-direction: column;
}

/* 与配置优化页面一致的标题区 */
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

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.console-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: #1a1a1a;
}

.instance-select {
  min-width: 280px;
}

.instance-select :deep(.ant-select-selector) {
  height: 36px !important;
  border-radius: 8px !important;
}

.reset-btn {
  border-radius: 6px;
  height: 36px;
}

/* 控制区与卡片样式，与配置优化页面保持一致 */
.control-section {
  margin-bottom: 24px;
}

.control-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.instance-selector {
  margin-bottom: 12px;
}

/* 侧边内容与编辑器在卡片中展示 */

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-title {
  font-weight: 600;
  color: #1a1a1a;
}

.refresh-db-btn {
  border-radius: 6px;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px;
  min-height: 0;
  max-height: 50vh;
}

.empty-state, .loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.empty-text {
  font-size: 14px;
}

.loading-state {
  flex-direction: row;
  gap: 8px;
}

.database-tree {
  padding: 8px 0;
}

.database-item {
  margin-bottom: 4px;
}

.database-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.database-header:hover {
  background: #f5f5f5;
}

.database-header.expanded {
  background: #e6f7ff;
}

.expand-icon {
  margin-right: 8px;
  font-size: 14px;
}

.database-name {
  flex: 1;
  font-weight: 500;
  color: #1a1a1a;
}



.table-list {
  margin-left: 20px;
  padding: 4px 0;
}

.table-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: #999;
  font-size: 12px;
}

.tables {
  padding: 4px 0;
}

.table-item {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.table-item:hover {
  background: #f0f0f0;
}

.table-item.active {
  background: #1890ff;
  color: white;
}

.table-icon {
  margin-right: 8px;
  font-size: 12px;
}

.table-name {
  flex: 1;
  font-size: 13px;
}

.table-type {
  font-size: 11px;
  opacity: 0.7;
}

.no-tables {
  padding: 8px 12px;
  color: #999;
  font-size: 12px;
  text-align: center;
}

.editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.editor-section {
  display: flex;
  flex-direction: column;
  height: 400px;
}

.editor-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.editor-title {
  font-weight: 600;
  color: #1a1a1a;
}

.editor-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.database-select {
  min-width: 150px;
}

.database-select :deep(.ant-select-selector) {
  height: 28px !important;
  border-radius: 6px !important;
}

.execute-btn {
  border-radius: 6px;
}

.editor-content {
  flex: 1;
  padding: 16px;
}

.sql-editor {
  height: 100%;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.sql-editor :deep(.ant-input) {
  height: 100%;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
}

/* 数据展示区卡片样式，与配置优化页面保持一致 */
.data-display-section {
  margin-bottom: 24px;
}

.data-display-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.results-tabs {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
}

.tab-item {
  padding: 12px 20px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  font-weight: 500;
}

.tab-item:hover {
  background: #f5f5f5;
}

.tab-item.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
  background: #f0f8ff;
}

.results-content {
  flex: 1;
  overflow: hidden;
}

.result-panel, .history-panel {
  height: 100%;
  padding: 16px;
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.result-data {
  height: 100%;
}

.table-result {
  height: 100%;
  overflow: auto;
}

.result-table :deep(.ant-table-tbody > tr > td) {
  padding: 8px 12px;
  font-size: 13px;
}

.text-result {
  height: 100%;
  overflow: auto;
}

.text-result pre {
  margin: 0;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

@media (max-width: 1200px) {
  .console-main {
    flex-direction: column;
  }
  
  .sidebar-container {
    width: 100%;
    height: 300px;
  }
}

/* 历史记录样式 */
.history-list {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 12px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 16px;
}

.history-count {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.clear-btn {
  border-radius: 6px;
  color: #ff4d4f;
  border-color: #ff4d4f;
}

.clear-btn:hover {
  background: #ff4d4f;
  color: white;
}

.history-items {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.history-item {
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  margin-bottom: 12px;
  padding: 12px;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.history-item.error {
  border-color: #ff7875;
  background: #fff2f0;
}

.history-item.error:hover {
  border-color: #ff4d4f;
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.1);
}

.history-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.history-time {
  font-size: 12px;
  color: #666;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.history-database {
  font-size: 12px;
  color: #1890ff;
  background: #e6f7ff;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.history-status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.history-status.success {
  color: #52c41a;
  background: #f6ffed;
}

.history-status.error {
  color: #ff4d4f;
  background: #fff2f0;
}

.history-duration {
  font-size: 11px;
  color: #999;
  font-family: monospace;
}

.history-actions {
  display: flex;
  gap: 6px;
}

.rerun-btn {
  border-radius: 4px;
  font-size: 12px;
  height: 24px;
  padding: 0 8px;
  color: #1890ff;
  border-color: #1890ff;
}

.rerun-btn:hover {
  background: #1890ff;
  color: white;
}

.delete-btn {
  border-radius: 4px;
  font-size: 12px;
  height: 24px;
  padding: 0 8px;
  color: #ff4d4f;
  border-color: #ff4d4f;
}

.delete-btn:hover {
  background: #ff4d4f;
  color: white;
}

.history-sql {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 8px;
}

.history-sql pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 120px;
  overflow-y: auto;
}

.history-error {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 6px;
  padding: 8px 12px;
  margin-top: 8px;
}

.error-label {
  font-size: 12px;
  font-weight: 500;
  color: #ff4d4f;
  margin-right: 8px;
}

.error-message {
  font-size: 12px;
  color: #a8071a;
  font-family: monospace;
}

/* 滚动条样式 */
.history-items::-webkit-scrollbar {
  width: 6px;
}

.history-items::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.history-items::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.history-items::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 侧边栏滚动条样式 */
.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
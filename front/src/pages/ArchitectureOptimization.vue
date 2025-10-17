<template>
  <div class="architecture-optimization-container">
    <!-- 页面标题区 -->
    <div class="config-header">
      <h2 class="config-title">架构优化分析</h2>
      <p class="config-desc">分析数据库架构性能并提供优化建议</p>
    </div>

    <!-- 实例选择和功能按钮区域 -->
    <div class="control-section">
      <a-card title="实例选择" class="control-card">
        <a-space direction="vertical" style="width: 100%">
          <!-- 实例选择器 -->
          <a-select 
            v-model:value="selectedInstance" 
            style="width: 100%; min-width: 300px" 
            placeholder="请选择要分析的实例"
            :loading="instanceLoading"
          >
            <a-select-option v-for="opt in instanceOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-select-option>
          </a-select>
          
          <!-- 功能按钮组 -->
          <a-space>
            <a-button 
              type="primary" 
              @click="loadData" 
              :loading="dataLoading"
              :disabled="!selectedInstance"
              class="load-data-btn"
            >
              获取数据
            </a-button>
            <a-button 
              type="primary" 
              @click="startAnalysis" 
              :loading="analysisLoading"
              :disabled="!dataLoaded || analysisLoading"
              class="start-analysis-btn"
            >
              开始分析
            </a-button>
          </a-space>
        </a-space>
      </a-card>
    </div>

    <!-- 数据展示卡片 -->
    <div class="data-display-section">
      <a-card title="数据展示" class="data-display-card">
        <!-- 初始状态：等待数据加载 -->
        <div v-if="!dataLoaded" class="waiting-state">
          <a-empty 
            description="等待数据加载"
            :image="emptyImage"
          >
            <template #description>
              <span class="waiting-text">请先选择实例并点击"获取数据"按钮</span>
            </template>
          </a-empty>
        </div>

        <!-- 数据加载完成状态 -->
        <div v-else class="data-loaded-state">
          <!-- 实时性能评分模块 -->
          <div class="performance-score-module">
            <h4>实时性能评分</h4>
            <a-row :gutter="24">
              <a-col :span="8">
                <div class="score-circle-container">
                  <a-progress 
                    type="circle" 
                    :percent="performanceScore.overall" 
                    :status="getScoreStatus(performanceScore.overall)"
                    :width="120"
                    :stroke-width="8"
                  >
                    <template #format="percent">
                      <div class="score-text">
                        <div class="score-number">{{ percent }}</div>
                        <div class="score-label">总分</div>
                      </div>
                    </template>
                  </a-progress>
                  <div class="score-description">
                    {{ getScoreDescription(performanceScore.overall) }}
                  </div>
                </div>
              </a-col>
              <a-col :span="16">
                <div class="score-details">
                  <a-row :gutter="16">
                    <a-col :span="12">
                      <div class="score-item">
                        <div class="score-item-header">
                          <span class="score-item-title">资源利用率</span>
                          <span class="score-item-value" :class="getScoreClass(performanceScore.cpu)">
                            {{ performanceScore.cpu }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="performanceScore.cpu" 
                          :status="getScoreStatus(performanceScore.cpu)"
                          size="small"
                          :show-info="false"
                        />
                      </div>
                    </a-col>
                    <a-col :span="12">
                      <div class="score-item">
                        <div class="score-item-header">
                          <span class="score-item-title">缓存效率</span>
                          <span class="score-item-value" :class="getScoreClass(performanceScore.memory)">
                            {{ performanceScore.memory }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="performanceScore.memory" 
                          :status="getScoreStatus(performanceScore.memory)"
                          size="small"
                          :show-info="false"
                        />
                      </div>
                    </a-col>
                  </a-row>
                  <a-row :gutter="16" style="margin-top: 16px;">
                    <a-col :span="12">
                      <div class="score-item">
                        <div class="score-item-header">
                          <span class="score-item-title">连接效率</span>
                          <span class="score-item-value" :class="getScoreClass(performanceScore.connection)">
                            {{ performanceScore.connection }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="performanceScore.connection" 
                          :status="getScoreStatus(performanceScore.connection)"
                          size="small"
                          :show-info="false"
                        />
                      </div>
                    </a-col>
                    <a-col :span="12">
                      <div class="score-item">
                        <div class="score-item-header">
                          <span class="score-item-title">查询性能</span>
                          <span class="score-item-value" :class="getScoreClass(performanceScore.query)">
                            {{ performanceScore.query }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="performanceScore.query" 
                          :status="getScoreStatus(performanceScore.query)"
                          size="small"
                          :show-info="false"
                        />
                      </div>
                    </a-col>
                  </a-row>
                </div>
              </a-col>
            </a-row>
            
            <!-- 评分说明 -->
            <div class="score-legend">
              <a-space>
                <a-tag color="green">90-100分：优秀</a-tag>
                <a-tag color="blue">80-89分：良好</a-tag>
                <a-tag color="orange">70-79分：一般</a-tag>
                <a-tag color="red">60-69分：较差</a-tag>
                <a-tag color="red">60分以下：需要优化</a-tag>
              </a-space>
            </div>
          </div>

          <a-divider />

          <!-- 实例基础信息 -->
          <a-descriptions title="实例基础信息" bordered :column="2">
            <a-descriptions-item label="实例名称">{{ instanceData.instanceName }}</a-descriptions-item>
            <a-descriptions-item label="数据库类型">{{ instanceData.dbType?.toUpperCase() }}</a-descriptions-item>
            <a-descriptions-item label="版本号">{{ performanceData.version }}</a-descriptions-item>
            <a-descriptions-item label="主机地址">{{ instanceData.host }}</a-descriptions-item>
            <a-descriptions-item label="端口">{{ instanceData.port }}</a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-tag :color="getStatusColor(instanceData.status)">
                {{ getStatusText(instanceData.status) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="慢查询开启状态">
              <a-tag :color="performanceData.slowQueryEnabled ? 'green' : 'red'">
                {{ performanceData.slowQueryEnabled ? '已开启' : '未开启' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="创建时间">{{ formatDateTime(instanceData.createTime) }}</a-descriptions-item>
          </a-descriptions>

          <a-divider />

          <!-- 性能指标概览 -->
          <div class="performance-metrics">
            <h4>性能指标概览</h4>
            
            <!-- 资源占用指标 -->
            <a-card size="small" title="资源占用" style="margin-bottom: 16px;">
              <a-row :gutter="16">
                <a-col :span="6">
                  <a-statistic title="CPU使用率" :value="performanceData.cpuUsage" suffix="%" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="内存使用率" :value="performanceData.memoryUsage" suffix="%" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="磁盘使用率" :value="performanceData.diskUsage" suffix="%" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="网络IO" :value="performanceData.networkIO" suffix="MB/s" />
                </a-col>
              </a-row>
            </a-card>

            <!-- 连接和事务指标 -->
            <a-card size="small" title="连接与事务" style="margin-bottom: 16px;">
              <a-row :gutter="16">
                <a-col :span="6">
                  <a-statistic title="活跃连接数" :value="performanceData.activeConnections" />
                </a-col>
                <a-col :span="6">
                  <a-statistic 
                    title="当前/最大连接数" 
                    :value="performanceData.currentConnections" 
                    :suffix="`/${performanceData.maxConnections}`" 
                  />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="高峰连接数" :value="performanceData.peakConnections" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="事务数" :value="performanceData.transactionCount" />
                </a-col>
              </a-row>
            </a-card>

            <!-- 查询性能指标 -->
            <a-card size="small" title="查询性能" style="margin-bottom: 16px;">
              <a-row :gutter="16">
                <a-col :span="6">
                  <a-statistic title="QPS" :value="performanceData.qps" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="平均查询耗时" :value="performanceData.avgQueryTime" suffix="ms" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="最慢查询" :value="performanceData.slowestQuery" suffix="ms" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="慢查询比例" :value="performanceData.slowQueryRatio" suffix="%" />
                </a-col>
              </a-row>
              <a-row :gutter="16" style="margin-top: 16px;">
                <a-col :span="8">
                  <a-statistic 
                    title="主从延迟" 
                    :value="isNumber(performanceData.replicationDelay) ? performanceData.replicationDelay : '—'" 
                    :suffix="isNumber(performanceData.replicationDelay) ? 'ms' : ''" 
                  />
                </a-col>
              </a-row>
            </a-card>

            <!-- 缓存和锁指标 -->
            <a-card size="small" title="缓存与并发控制">
              <a-row :gutter="16">
                <a-col :span="6">
                  <a-statistic title="Buffer Pool命中率" :value="performanceData.bufferPoolHitRate" suffix="%" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="Shared Buffer命中率" :value="performanceData.sharedBufferHitRate" suffix="%" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="锁等待次数" :value="performanceData.lockWaits" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="死锁次数" :value="performanceData.deadlocks" />
                </a-col>
              </a-row>
            </a-card>
          </div>

          <a-alert 
            message="数据加载完成" 
            description="实例数据已成功加载，现在可以开始架构分析。" 
            type="success" 
            show-icon 
            style="margin-top: 16px"
          />
        </div>
      </a-card>
    </div>

    <!-- 分析结果卡片（动态添加） -->
    <div v-if="analysisResult" class="analysis-result-section">
      <a-card title="分析结果" class="analysis-result-card">
        <a-descriptions title="总体建议" bordered :column="1" v-if="analysisResult.advice && analysisResult.advice.length">
          <a-descriptions-item v-for="(adv, idx) in analysisResult.advice" :key="idx" :label="adv.type || '建议'">
            {{ adv.message }}
          </a-descriptions-item>
        </a-descriptions>

        <a-divider />

        <a-list v-if="analysisResult.risks && analysisResult.risks.length" :data-source="analysisResult.risks" header="风险项" bordered>
          <template #renderItem="{ item }">
            <a-list-item>
              <a-tag :color="item.severity === 'critical' ? 'red' : (item.severity === 'warning' ? 'orange' : 'blue')" style="margin-right:8px;">
                {{ item.severity || 'info' }}
              </a-tag>
              <strong style="margin-right:8px;">{{ item.type }}</strong>
              <span>{{ item.message }}</span>
            </a-list-item>
          </template>
        </a-list>

        <a-alert v-else message="暂无风险项" type="success" show-icon />
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { Empty } from 'ant-design-vue';
import apiClient from '../utils/apiClient';

// 响应式数据
const instanceLoading = ref(false);
const dataLoading = ref(false);
const analysisLoading = ref(false);
const instanceOptions = ref([]);
const selectedInstance = ref('');
const dataLoaded = ref(false);
const instanceData = ref({});
const performanceData = ref({});
const performanceScore = ref({
  overall: 0,
  cpu: 0,
  memory: 0,
  connection: 0,
  query: 0
});
const analysisResult = ref(null);

// 空状态图片
const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE;

// 加载实例列表
async function loadInstances() {
  try {
    instanceLoading.value = true;
    const data = await apiClient.getInstances();
    const list = Array.isArray(data) ? data : (Array.isArray(data?.instances) ? data.instances : []);
    instanceOptions.value = list.filter(i => i.status === 'running').map(i => ({
      value: String(i.id),
      label: `${i.instanceName} (${i.dbType}) ${i.host}:${i.port}`
    }));
  } catch (error) {
    message.error('加载实例列表失败');
    instanceOptions.value = [];
  } finally {
    instanceLoading.value = false;
  }
}

// 获取数据
async function loadData() {
  if (!selectedInstance.value) {
    message.warning('请先选择实例');
    return;
  }

  try {
    dataLoading.value = true;
    // 1) 获取实例详细信息（用于基础信息展示）
    const instanceInfo = await apiClient.getInstance(Number(selectedInstance.value));
    instanceData.value = instanceInfo || {};

    // 2) 调用后端架构分析接口，直接使用后端采集与评分
    const res = await apiClient.analyzeArchitecture(Number(selectedInstance.value));

    // 获取数据阶段不展示分析结果卡片，保持为空
    analysisResult.value = null;

    // 映射后端性能数据到页面字段
    const perf = res?.performance || {};
    const inst = res?.instance || instanceData.value || {};
    performanceData.value = {
      version: inst.version || instanceData.value?.version || 'unknown',
      cpuUsage: perf.cpuUsage ?? 0,
      memoryUsage: perf.memoryUsage ?? 0,
      diskUsage: perf.diskUsage ?? 0,
      networkIO: perf.networkIO ?? 0,
      replicationDelay: (typeof perf.replicationDelay === 'number' ? perf.replicationDelay : null),
      activeConnections: perf.activeConnections ?? 0,
      currentConnections: perf.currentConnections ?? 0,
      maxConnections: perf.maxConnections ?? 0,
      peakConnections: perf.peakConnections ?? 0,
      transactionCount: perf.transactionCount ?? 0,
      lockWaits: perf.lockWaits ?? 0,
      deadlocks: perf.deadlocks ?? 0,
      bufferPoolHitRate: perf.bufferPoolHitRate ?? 0,
      sharedBufferHitRate: perf.sharedBufferHitRate ?? (perf.bufferPoolHitRate ?? 0),
      qps: perf.qps ?? 0,
      slowQueryEnabled: perf.slowQueryEnabled ?? false,
      slowestQuery: perf.slowestQuery ?? 0,
      slowQueryRatio: perf.slowQueryRatio ?? 0,
      avgQueryTime: perf.avgQueryTime ?? 0
    };

    // 3) 使用后端评分数据
    const sc = res?.score || {};
    performanceScore.value = {
      overall: parseInt(sc.overall ?? 0, 10) || 0,
      cpu: parseInt(sc.resource ?? 0, 10) || 0,
      memory: parseInt(sc.cache ?? 0, 10) || 0,
      connection: parseInt(sc.connection ?? 0, 10) || 0,
      query: parseInt(sc.query ?? 0, 10) || 0
    };
    
    dataLoaded.value = true;
    message.success('数据加载完成（后端采集与评分）');
  } catch (error) {
    message.error('数据加载失败');
    dataLoaded.value = false;
  } finally {
    dataLoading.value = false;
  }
}

// 开始分析
async function startAnalysis() {
  if (!dataLoaded.value) {
    message.warning('请先获取数据');
    return;
  }

  try {
    analysisLoading.value = true;
    // 调用后端架构分析接口
    const res = await apiClient.analyzeArchitecture(Number(selectedInstance.value));

    // 保存分析结果原始数据
    analysisResult.value = res || {};

    // 将后端性能数据映射到页面的性能展示模块
    const perf = res?.performance || {};
    const inst = res?.instance || instanceData.value || {};
    performanceData.value = {
      version: inst.version || instanceData.value?.version || 'unknown',
      cpuUsage: perf.cpuUsage ?? 0,
      memoryUsage: perf.memoryUsage ?? 0,
      diskUsage: perf.diskUsage ?? 0,
      networkIO: perf.networkIO ?? 0,
      replicationDelay: perf.replicationDelay ?? 0,
      activeConnections: perf.activeConnections ?? 0,
      currentConnections: perf.currentConnections ?? 0,
      maxConnections: perf.maxConnections ?? 0,
      peakConnections: perf.peakConnections ?? 0,
      transactionCount: perf.transactionCount ?? 0,
      lockWaits: perf.lockWaits ?? 0,
      deadlocks: perf.deadlocks ?? 0,
      bufferPoolHitRate: perf.bufferPoolHitRate ?? 0,
      sharedBufferHitRate: perf.sharedBufferHitRate ?? (perf.bufferPoolHitRate ?? 0),
      qps: perf.qps ?? 0,
      slowQueryEnabled: perf.slowQueryEnabled ?? false,
      slowestQuery: perf.slowestQuery ?? 0,
      slowQueryRatio: perf.slowQueryRatio ?? 0,
      avgQueryTime: perf.avgQueryTime ?? 0
    };

    // 使用后端评分
    const sc = res?.score || {};
    performanceScore.value = {
      overall: parseInt(sc.overall ?? 0, 10) || 0,
      cpu: parseInt(sc.resource ?? 0, 10) || 0,
      memory: parseInt(sc.cache ?? 0, 10) || 0,
      connection: parseInt(sc.connection ?? 0, 10) || 0,
      query: parseInt(sc.query ?? 0, 10) || 0
    };
    message.success('架构分析完成（后端评分）');
  } catch (error) {
    message.error(error?.message || '分析失败，请检查后端服务');
  } finally {
    analysisLoading.value = false;
  }
}

// 工具函数
function getStatusColor(status) {
  const colorMap = {
    'running': 'green',
    'stopped': 'red',
    'error': 'red',
    'pending': 'orange'
  };
  return colorMap[status] || 'default';
}

function getStatusText(status) {
  const textMap = {
    'running': '运行中',
    'stopped': '已停止',
    'error': '错误',
    'pending': '待启动'
  };
  return textMap[status] || status;
}

function formatDateTime(dateTime) {
  if (!dateTime) return '-';
  try {
    const val = typeof dateTime === 'string' ? dateTime.replace(' ', 'T') : dateTime;
    const d = new Date(val);
    if (isNaN(d.getTime())) return String(dateTime);
    return d.toLocaleString('zh-CN');
  } catch {
    return String(dateTime);
  }
}

function isNumber(x) {
  return typeof x === 'number' && !isNaN(x);
}

function getScoreStatus(score) {
  if (score >= 90) return 'success';
  if (score >= 70) return 'normal';
  return 'exception';
}

function getScoreClass(score) {
  if (score >= 90) return 'score-excellent';
  if (score >= 80) return 'score-good';
  if (score >= 70) return 'score-normal';
  if (score >= 60) return 'score-poor';
  return 'score-bad';
}

function getScoreDescription(score) {
  if (score >= 90) return '性能一般';
  if (score >= 80) return '良好';
  if (score >= 70) return '一般';
  if (score >= 60) return '较差';
  return '需要优化';
}

// 本地评分逻辑已移除，统一使用后端返回的评分

onMounted(() => {
  loadInstances();
});
</script>

<style scoped>
.architecture-optimization-container {
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

.data-display-section {
  margin-bottom: 24px;
}

.data-display-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.waiting-state {
  padding: 40px 0;
  text-align: center;
}

.waiting-text {
  color: #999;
  font-size: 16px;
}

.loading-state {
  padding: 40px 0;
  text-align: center;
}

.data-loaded-state {
  animation: fadeInUp 0.6s ease-out;
}

.analysis-result-section {
  animation: slideInUp 0.6s ease-out;
}

.loading-content {
  background: #f5f5f5;
  padding: 24px;
  border-radius: 8px;
}

.performance-score-module {
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid #e8e8e8;
}

.performance-score-module h4 {
  margin-bottom: 20px;
  color: #262626;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-circle-container {
  text-align: center;
}

.score-text {
  text-align: center;
}

.score-number {
  font-size: 24px;
  font-weight: bold;
  color: #1890ff;
}

.score-label {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.score-description {
  margin-top: 12px;
  font-size: 14px;
  color: #666;
}

.score-details {
  padding-left: 24px;
}

.score-item {
  margin-bottom: 16px;
}

.score-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.score-item-title {
  font-size: 14px;
  color: #666;
}

.score-item-value {
  font-size: 16px;
  font-weight: 600;
}

.score-excellent {
  color: #52c41a;
}

.score-good {
  color: #1890ff;
}

.score-normal {
  color: #faad14;
}

.score-poor {
  color: #ff7875;
}

.score-bad {
  color: #ff4d4f;
}

.score-legend {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.performance-metrics h4 {
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
}

.analysis-result-section {
  margin-top: 24px;
}

.analysis-result-card {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 20px;
  background: #fff;
  border: 1px solid #f0f0f0;
}

.analysis-result-card h4 {
  margin-bottom: 16px;
  color: #262626;
  font-weight: 600;
  font-size: 16px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
}

.load-data-btn, .start-analysis-btn {
  min-width: 100px;
}



/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    padding: 16px;
    margin-bottom: 16px;
  }
  
  .page-title {
    font-size: 20px;
  }
  
  .page-desc {
    font-size: 12px;
  }
  
  .control-card,
  .data-display-card {
    padding: 16px;
    margin-bottom: 16px;
  }
  
  .performance-score-module {
    padding: 16px;
    margin-bottom: 16px;
  }
  
  .analysis-result {
    padding: 16px;
    margin-top: 16px;
  }
  
  .waiting-state,
  .loading-state {
    padding: 30px 16px;
  }
  
  .ant-btn {
    height: 32px;
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .page-header {
    padding: 12px;
  }
  
  .page-title {
    font-size: 18px;
  }
  
  .control-card,
  .data-display-card,
  .performance-score-module,
  .analysis-result {
    padding: 12px;
  }
  
  .waiting-state,
  .loading-state {
    padding: 20px 12px;
  }
}

/* 评分样式类 */
.score-excellent { color: #52c41a; }
.score-good { color: #1890ff; }
.score-normal { color: #faad14; }
.score-poor { color: #ff7a45; }
.score-critical { color: #ff4d4f; }

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
</style>
<template>
  <div class="config-optimization-container">
    <!-- 页面标题区 -->
    <div class="config-header">
      <h2 class="config-title">配置优化分析</h2>
      <p class="config-desc">分析数据库配置参数并提供优化建议</p>
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
      <a-card title="配置数据" class="data-display-card">
        <!-- 初始状态：等待数据加载 -->
        <div v-if="!dataLoaded" class="waiting-state">
          <a-empty 
            description="等待数据加载"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          >
            <template #description>
              <span style="color: #999;">请先选择实例并点击"获取数据"按钮</span>
            </template>
          </a-empty>
        </div>

        <!-- 数据加载完成状态 -->
        <div v-else class="data-loaded-state">
          <!-- 实时配置评分模块 -->
          <div class="config-score-module">
            <h4>实时配置评分</h4>
            <a-row :gutter="24">
              <a-col :span="8">
                <div class="score-circle-container">
                  <a-progress 
                    type="circle" 
                    :percent="configScore.overall" 
                    :status="getScoreStatus(configScore.overall)"
                    :width="120"
                    :stroke-width="8"
                    :stroke-color="getScoreColor(configScore.overall)"
                  >
                    <template #format="percent">
                      <div class="score-text">
                        <div class="score-number">{{ percent }}</div>
                        <div class="score-label">总分</div>
                      </div>
                    </template>
                  </a-progress>
                  <div class="score-description">
                    {{ getScoreDescription(configScore.overall) }}
                  </div>
                </div>
              </a-col>
              <a-col :span="16">
                <div class="score-details">
                  <a-row :gutter="16">
                    <a-col :span="12">
                      <div class="score-item">
                        <div class="score-item-header">
                          <span class="score-item-title">系统配置</span>
                          <span class="score-item-value" :class="getScoreClass(configScore.system)">
                            {{ configScore.system }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="configScore.system" 
                          :status="getScoreStatus(configScore.system)"
                          :stroke-color="getScoreColor(configScore.system)"
                          size="small"
                          :show-info="false"
                        />
                      </div>
                    </a-col>
                    <a-col :span="12">
                      <div class="score-item">
                        <div class="score-item-header">
                          <span class="score-item-title">MySQL配置</span>
                          <span class="score-item-value" :class="getScoreClass(configScore.mysql)">
                            {{ configScore.mysql }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="configScore.mysql" 
                          :status="getScoreStatus(configScore.mysql)"
                          :stroke-color="getScoreColor(configScore.mysql)"
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
                          <span class="score-item-title">性能优化</span>
                          <span class="score-item-value" :class="getScoreClass(configScore.performance)">
                            {{ configScore.performance }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="configScore.performance" 
                          :status="getScoreStatus(configScore.performance)"
                          :stroke-color="getScoreColor(configScore.performance)"
                          size="small"
                          :show-info="false"
                        />
                      </div>
                    </a-col>
                    <a-col :span="12">
                      <div class="score-item">
                        <div class="score-item-header">
                          <span class="score-item-title">安全配置</span>
                          <span class="score-item-value" :class="getScoreClass(configScore.security)">
                            {{ configScore.security }}分
                          </span>
                        </div>
                        <a-progress 
                          :percent="configScore.security" 
                          :status="getScoreStatus(configScore.security)"
                          :stroke-color="getScoreColor(configScore.security)"
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
                <a-tag color="volcano">0-59分：急需优化</a-tag>
              </a-space>
            </div>
          </div>

          <a-divider />

          <!-- 系统层指标 -->
          <a-card size="small" title="系统层指标" style="margin-bottom: 16px;" class="metric-card">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-statistic 
                  title="CPU利用率" 
                  :value="configData.systemMetrics.cpuUsage" 
                  suffix="%" 
                  :value-style="getMetricStyle(configData.systemMetrics.cpuUsage, 'cpu')"
                />
              </a-col>
              <a-col :span="8">
                <a-statistic 
                  title="内存使用率" 
                  :value="configData.systemMetrics.memoryUsage" 
                  suffix="%" 
                  :value-style="getMetricStyle(configData.systemMetrics.memoryUsage, 'memory')"
                />
              </a-col>
              <a-col :span="8">
                <a-statistic 
                  title="磁盘I/O延迟" 
                  :value="configData.systemMetrics.diskIOLatency" 
                  suffix="ms" 
                  :value-style="getMetricStyle(configData.systemMetrics.diskIOLatency, 'disk')"
                />
              </a-col>
            </a-row>
          </a-card>

          <!-- MySQL核心指标 -->
          <a-card size="small" title="MySQL核心指标" style="margin-bottom: 16px;" class="metric-card">
            <a-row :gutter="16">
              <a-col :span="6">
                <a-statistic 
                  title="缓存命中率" 
                  :value="configData.mysqlMetrics.bufferPoolHitRate" 
                  suffix="%" 
                  :value-style="getMetricStyle(configData.mysqlMetrics.bufferPoolHitRate, 'cache')"
                />
              </a-col>
              <a-col :span="6">
                <a-statistic 
                  title="活跃连接数" 
                  :value="configData.mysqlMetrics.activeConnections" 
                  :value-style="getMetricStyle(configData.mysqlMetrics.activeConnections, 'connections')"
                />
              </a-col>
              <a-col :span="6">
                <a-statistic 
                  title="慢查询比例" 
                  :value="configData.mysqlMetrics.slowQueryRatio" 
                  suffix="%" 
                  :value-style="getMetricStyle(configData.mysqlMetrics.slowQueryRatio, 'slowquery')"
                />
              </a-col>
              <a-col :span="6">
                <a-statistic 
                  title="平均响应时间" 
                  :value="configData.mysqlMetrics.avgResponseTime" 
                  suffix="ms" 
                  :value-style="getMetricStyle(configData.mysqlMetrics.avgResponseTime, 'response')"
                />
              </a-col>
            </a-row>
            <a-row :gutter="16" style="margin-top: 16px;">
              <a-col :span="6">
                <a-statistic 
                  title="锁等待时间" 
                  :value="configData.mysqlMetrics.lockWaitTime" 
                  suffix="ms" 
                  :value-style="getMetricStyle(configData.mysqlMetrics.lockWaitTime, 'lock')"
                />
              </a-col>
              <a-col :span="6">
                <a-statistic 
                  title="死锁次数" 
                  :value="configData.mysqlMetrics.deadlockCount" 
                  :value-style="getMetricStyle(configData.mysqlMetrics.deadlockCount, 'deadlock')"
                />
              </a-col>
              <a-col :span="6">
                <a-statistic 
                  title="索引使用率" 
                  :value="configData.mysqlMetrics.indexUsageRate" 
                  suffix="%" 
                  :value-style="getMetricStyle(configData.mysqlMetrics.indexUsageRate, 'index')"
                />
              </a-col>
            </a-row>
          </a-card>

          <!-- 性能指标 -->
          <a-card size="small" title="性能指标" class="metric-card">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-statistic 
                  title="QPS" 
                  :value="configData.performanceMetrics.qps" 
                  :value-style="getMetricStyle(configData.performanceMetrics.qps, 'qps')"
                />
              </a-col>
              <a-col :span="8">
                <a-statistic 
                  title="TPS" 
                  :value="configData.performanceMetrics.tps" 
                  :value-style="getMetricStyle(configData.performanceMetrics.tps, 'tps')"
                />
              </a-col>
              <a-col :span="8">
                <a-statistic 
                  title="P95时延" 
                  :value="configData.performanceMetrics.p95Latency" 
                  suffix="ms" 
                  :value-style="getMetricStyle(configData.performanceMetrics.p95Latency, 'latency')"
                />
              </a-col>
            </a-row>
              <a-row :gutter="16" style="margin-top: 16px;">
              <a-col :span="12">
                <a-statistic 
                  title="Redo/WAL写入延迟" 
                  :value="isNumber(configData.performanceMetrics.redoWalLatency) ? configData.performanceMetrics.redoWalLatency : '—'" 
                  :precision="isNumber(configData.performanceMetrics.redoWalLatency) ? 3 : 0"
                  :suffix="isNumber(configData.performanceMetrics.redoWalLatency) ? 'ms' : ''" 
                  :value-style="getMetricStyle(configData.performanceMetrics.redoWalLatency, 'redo')"
                />
              </a-col>
            </a-row>
          </a-card>

          <a-alert 
            message="数据加载完成" 
            description="配置数据已成功加载，现在可以开始配置分析。" 
            type="success" 
            show-icon 
            style="margin-top: 16px"
          />
        </div>
      </a-card>
    </div>

    <!-- 分析结果卡片（动态添加） -->
    <div v-if="analysisResult" class="analysis-result-section">
      <a-card title="配置优化分析结果" class="analysis-result-card">
        <!-- 空白内容区域 -->
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { message, Empty } from 'ant-design-vue';
import apiClient from '../utils/apiClient';
import globalInstances from '../utils/globalInstances';

let cacheClearedHandler = null;

// 响应式数据
const instanceLoading = ref(false);
const dataLoading = ref(false);
const analysisLoading = ref(false);
const instanceOptions = ref([]);
const selectedInstance = ref('');
const dataLoaded = ref(false);
const configData = ref({});
const analysisResult = ref(null);
const configScore = ref({
  overall: 0,
  system: 0,
  mysql: 0,
  performance: 0,
  security: 0
});

// 判断是否为有效数字（用于统计组件的动态显示）
function isNumber(value) {
  return typeof value === 'number' && !Number.isNaN(value);
}

// 使用全局状态管理加载运行中的实例
async function loadInstances() {
  try {
    instanceLoading.value = true;
    // 确保全局数据已加载
    await globalInstances.ensureInstancesLoaded();
    
    // 获取运行中的实例
    const runningInstances = globalInstances.getRunningInstances();
    
    // 格式化选项
    instanceOptions.value = runningInstances.map(i => ({
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

    // 从后端采集真实指标摘要（带 6 秒窗口二次采样）
    const summary = await apiClient.getConfigSummary(Number(selectedInstance.value), 6);
    const sys = summary?.system || {};
    const mysql = summary?.mysql || {};
    const perf = summary?.perf || {};
    const score = summary?.score || null;

    const toNum = (x, d = 0) => {
      const n = Number(x);
      return x === null || x === undefined || Number.isNaN(n) ? d : n;
    };
    const toNullableNum = (x) => {
      const n = Number(x);
      return x === null || x === undefined || Number.isNaN(n) ? null : n;
    };

    configData.value = {
      systemMetrics: {
        cpuUsage: toNum(sys.cpu_usage, 0),
        memoryUsage: toNum(sys.memory_usage, 0),
        // 使用后端提供的磁盘 I/O 延迟（psutil 估算），缺失时回退到 p95 延迟
        diskIOLatency: toNum(perf.io_latency_ms ?? perf.p95_latency_ms, 0)
      },
      mysqlMetrics: {
        bufferPoolHitRate: toNum(mysql.cache_hit_rate, 0),
        activeConnections: toNum(mysql.threads_running, 0),
        slowQueryRatio: toNum(mysql.slow_query_ratio, 0),
        avgResponseTime: toNum(mysql.avg_response_time_ms, 0),
        lockWaitTime: toNum(mysql.innodb_row_lock_time_ms, 0),
        deadlockCount: toNum(mysql.deadlocks, 0),
        indexUsageRate: toNum(mysql.index_usage_rate, 0)
      },
      performanceMetrics: {
        qps: toNum(perf.qps, 0),
        tps: toNum(perf.tps, 0),
        p95Latency: toNum(perf.p95_latency_ms, 0),
        // 保留 null 表示无数据，避免与真实 0ms 混淆
        redoWalLatency: toNullableNum(perf.redo_write_latency_ms)
      }
    };

    dataLoaded.value = true;

    // 仅使用后端评分；若缺失则置0，不再进行前端兜底计算
    const toInt = (x, d = 0) => {
      const n = parseInt(x, 10);
      return Number.isNaN(n) ? d : Math.max(0, Math.min(100, n));
    };
    const sc = (score && typeof score === 'object') ? score : {};
    configScore.value = {
      overall: toInt(sc.overall, 0),
      system: toInt(sc.system, 0),
      mysql: toInt(sc.mysql, 0),
      performance: toInt(sc.performance, 0),
      security: toInt(sc.security, 0),
    };
    message.success('数据加载完成（后端指标与评分）');
  } catch (error) {
    message.error('数据加载失败');
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

    // 调用后端生成配置优化建议（DeepSeek，若未配置将返回降级信息）
    const advise = await apiClient.getConfigAdvice(Number(selectedInstance.value));
    analysisResult.value = {
      overallScore: configScore.value.overall,
      recommendations: advise?.advice || null,
      backendError: advise?.error || null
    };

    message.success('配置分析完成（后端建议已返回）');
  } catch (error) {
    message.error('分析失败');
  } finally {
    analysisLoading.value = false;
  }
}

// 已移除前端评分兜底逻辑，统一依赖后端返回的评分

// 获取指标样式
function getMetricStyle(value, type) {
  const thresholds = {
    cpu: { good: 50, warning: 70 },
    memory: { good: 70, warning: 85 },
    disk: { good: 10, warning: 20 },
    cache: { good: 95, warning: 90 },
    connections: { good: 100, warning: 200 },
    slowquery: { good: 1, warning: 3 },
    response: { good: 20, warning: 50 },
    lock: { good: 5, warning: 10 },
    deadlock: { good: 2, warning: 5 },
    index: { good: 90, warning: 80 },
    qps: { good: 1000, warning: 500 },
    tps: { good: 800, warning: 400 },
    latency: { good: 20, warning: 50 },
    redo: { good: 5, warning: 10 }
  };
  
  const threshold = thresholds[type];
  if (!threshold) return { color: '#1890ff' };
  
  if (type === 'cache' || type === 'index') {
    // 越高越好的指标
    if (value >= threshold.good) return { color: '#52c41a' };
    if (value >= threshold.warning) return { color: '#faad14' };
    return { color: '#ff4d4f' };
  } else {
    // 越低越好的指标
    if (value <= threshold.good) return { color: '#52c41a' };
    if (value <= threshold.warning) return { color: '#faad14' };
    return { color: '#ff4d4f' };
  }
}

// 获取评分状态
function getScoreStatus(score) {
  if (score >= 90) return 'success';
  if (score >= 70) return 'normal';
  return 'exception';
}

// 获取评分颜色
function getScoreColor(score) {
  if (score >= 90) return '#52c41a';
  if (score >= 70) return '#faad14';
  return '#ff4d4f';
}

// 获取评分描述
function getScoreDescription(score) {
  if (score >= 90) return '配置优秀';
  if (score >= 80) return '配置良好';
  if (score >= 70) return '配置一般';
  if (score >= 60) return '需要优化';
  return '急需优化';
}

// 获取评分样式类
function getScoreClass(score) {
  if (score >= 90) return 'score-excellent';
  if (score >= 80) return 'score-good';
  if (score >= 70) return 'score-normal';
  if (score >= 60) return 'score-poor';
  return 'score-critical';
}

// 组件挂载时加载实例列表
onMounted(() => {
  loadInstances();
  cacheClearedHandler = () => {
    instanceOptions.value = [];
    loadInstances();
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
.config-optimization-container {
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

.load-data-btn, .start-analysis-btn {
  min-width: 100px;
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

.data-loaded-state {
  animation: fadeInUp 0.6s ease-out;
}

.metric-card {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
}

.metric-card .ant-card-head {
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.analysis-result-section {
  animation: slideInUp 0.6s ease-out;
}

.analysis-result-card {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid #e8f4fd;
}

/* 配置评分模块样式 */
.config-score-module {
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid #e8e8e8;
}

.config-score-module h4 {
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
  color: #262626;
}

.score-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.score-description {
  margin-top: 12px;
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.score-details {
  padding-left: 20px;
}

.score-item {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.score-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.score-item-title {
  font-size: 14px;
  color: #262626;
  font-weight: 500;
}

.score-item-value {
  font-size: 14px;
  font-weight: 600;
}

.score-legend {
  margin-top: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  border: 1px solid #f0f0f0;
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

/* 响应式设计 */
@media (max-width: 768px) {
  .config-header {
    padding: 16px;
    margin-bottom: 16px;
  }
  
  .config-title {
    font-size: 20px;
  }
  
  .config-desc {
    font-size: 12px;
  }
  
  .control-section,
  .data-section {
    margin-bottom: 16px;
  }
  
  .control-section .ant-card,
  .data-section .ant-card {
    margin-bottom: 16px;
  }
  
  .metric-card .ant-col {
    margin-bottom: 16px;
  }
  
  .waiting-display,
  .loading-display {
    padding: 30px 16px;
  }
  
  .ant-btn {
    height: 32px;
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .config-header {
    padding: 12px;
  }
  
  .config-title {
    font-size: 18px;
  }
  
  .control-section .ant-card,
  .data-section .ant-card {
    padding: 12px;
  }
  
  .waiting-display,
  .loading-display {
    padding: 20px 12px;
  }
}
</style>
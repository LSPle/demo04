import React, { useEffect, useMemo, useState } from 'react';
import { Card, Select, Button, Space, message, Row, Col, Skeleton, Alert } from 'antd';
import { DatabaseOutlined, BulbOutlined, LineChartOutlined } from '@ant-design/icons';
import apiClient from '../utils/apiClient';
import { useInstances } from '../contexts/InstanceContext';
import { renderAnalysis } from '../utils/commonUtils';

// 轻量 Markdown 清洗（与其它页面风格一致）
const stripMarkdownLite = (s) => {
  if (!s || typeof s !== 'string') return '';
  let t = s.replace(/```[\s\S]*?```/g, '');
  t = t.replace(/`([^`]+)`/g, '$1');
  t = t.replace(/\*\*([^*]+)\*\*/g, '$1');
  t = t.replace(/\*([^*]+)\*/g, '$1');
  t = t.replace(/^#+\s*/gm, '');
  t = t.replace(/^[-*+]\s*/gm, '• ');
  return t.trim();
};

// 指标映射到友好中文标签
const METRIC_LABELS = {
  cpu: 'CPU利用率',
  mem: '内存使用率',
  cache_hit: '缓存命中率',
  io_latency_ms: '磁盘I/O延迟',
  threads_running: '活跃连接数',
  qps: 'QPS',
  tps: 'TPS',
  slow_ratio: '慢查询比例',
  avg_latency_ms: '平均响应时间',
  p95_latency_ms: 'P95时延',
  lock_wait_ms: '锁等待时间',
  deadlocks: '死锁次数',
  redo_latency_ms: 'Redo/WAL写入延迟',
  index_usage: '索引使用率',
};

// 新增：数值格式化与严重度计算，驱动视觉层次与颜色
const formatValue = (val, unit = '') => {
  if (val === null || val === undefined || val === '') return 'N/A';
  return `${val}${unit}`;
};

//可能要删除
const getSeverity = (key, rawVal) => {
  const v = Number(rawVal);
  if (rawVal === null || rawVal === undefined || rawVal === '' || Number.isNaN(v)) return 'default';
  switch (key) {
    case 'cpu':
    case 'mem':
      if (v >= 85) return 'bad';
      if (v >= 65) return 'warn';
      return 'ok';
    case 'cache_hit':
      if (v < 80) return 'bad';
      if (v < 90) return 'warn';
      return 'ok';
    case 'io_latency_ms':
      if (v >= 30) return 'bad';
      if (v >= 15) return 'warn';
      return 'ok';
    case 'p95_latency_ms':
      if (v >= 3000) return 'bad';
      if (v >= 1500) return 'warn';
      return 'ok';
    case 'threads_running':
      if (v >= 400) return 'bad';
      if (v >= 200) return 'warn';
      return 'default';
    case 'lock_wait_ms':
      if (v >= 500) return 'bad';
      if (v >= 100) return 'warn';
      return 'ok';
    case 'deadlocks':
      return v > 0 ? 'bad' : 'ok';
    case 'redo_latency_ms':
      if (v >= 50) return 'bad';
      if (v >= 20) return 'warn';
      return 'ok';
    // 对于 QPS/TPS/指数等正向指标，不做警示，仅默认展示
    default:
      return 'default';
  }
};

const AdviceCard = ({ text, status }) => {
  if (status === 'error') {
    return (
      <Alert 
        type="warning" 
        showIcon 
        message="AI未启用或分析失败" 
        description="DeepSeek未配置或网络超时。可稍后重试。" 
      />
    );
  }
  if (!text) {
    return (
      <Alert 
        type="info" 
        showIcon 
        message="暂无AI建议" 
        description="请先执行分析，或稍后重试。" 
      />
    );
  }
  
  // 使用与架构优化页面相同的渲染方式，确保层次清晰
  return (
    <Alert
      className="analysis-alert"
      message={
        <span style={{ 
          fontSize: '15px', 
          fontWeight: 600,
          color: '#1890ff',
          display: 'flex',
          alignItems: 'center'
        }}>
          <BulbOutlined style={{ marginRight: 6 }} />
          配置优化建议
        </span>
      }
      description={renderAnalysis(text)}
      type="info"
      showIcon={false}
      style={{ 
        marginBottom: 0,
        borderRadius: '12px',
        border: '1px solid #e8f4ff',
        background: 'linear-gradient(135deg, #fafcff 0%, #f0f9ff 100%)'
      }}
    />
  );
};

const ConfigOptimization = () => {
  const { getRunningInstanceOptions } = useInstances();
  const instanceOptions = getRunningInstanceOptions();
  const [selectedInstance, setSelectedInstance] = useState('');
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [advice, setAdvice] = useState('');
  const [adviceStatus, setAdviceStatus] = useState('idle'); // idle|loading|success|error

  // 分析函数
  const handleAnalyze = async () => {
    if (!selectedInstance) {
      message.warning('请先选择数据库实例');
      return;
    }
    setLoading(true);
    setAdviceStatus('loading');
    try {
      // 一次调用后端建议接口，返回 metrics + advice
      
      const data = await apiClient.getMetricsAdvice(selectedInstance);
      const summary = data.metrics || null;
      setMetrics(summary);

      // 处理AI建议内容（清洗无关格式，保持原文）
      const txt = stripMarkdownLite(data.advice || '');
      setAdvice(txt);
      setAdviceStatus(data.error ? 'error' : (txt ? 'success' : 'idle'));

      message.success('分析完成');
    } catch (e) {
      console.error(e);
      setAdviceStatus('error');
      message.error('分析失败');
    } finally {
      setLoading(false);
    }
  };

  // 当实例选择无效时重置
  useEffect(() => {
    if (selectedInstance && !instanceOptions.some(opt => opt.value === selectedInstance)) {
      setSelectedInstance('');
      setMetrics(null);
      setAdvice('');
      setAdviceStatus('idle');
      message.warning('所选实例已不可用，选择已重置');
    }
  }, [selectedInstance, instanceOptions]);

  // 将后端 summary 映射到指标
  const metricItems = useMemo(() => {
    if (!metrics) return [];
    
    const s = metrics;
    const sys = s.system || {};
    const mysql = s.mysql || {};
    const perf = s.perf || {};
    
    return [
      { key: 'cpu', label: METRIC_LABELS.cpu, value: sys.cpu_usage, unit: '%' },
      { key: 'mem', label: METRIC_LABELS.mem, value: sys.memory_usage, unit: '%' },
      { key: 'cache_hit', label: METRIC_LABELS.cache_hit, value: mysql.cache_hit_rate, unit: '%' },
      { key: 'io_latency_ms', label: METRIC_LABELS.io_latency_ms, value: perf.io_latency_ms, unit: ' ms' },
      { key: 'threads_running', label: METRIC_LABELS.threads_running, value: mysql.threads_running },
      { key: 'qps', label: METRIC_LABELS.qps, value: perf.qps },
      { key: 'tps', label: METRIC_LABELS.tps, value: perf.tps },
      { key: 'slow_ratio', label: METRIC_LABELS.slow_ratio, value: mysql.slow_query_ratio, unit: '%' },
      { key: 'avg_latency_ms', label: METRIC_LABELS.avg_latency_ms, value: mysql.avg_response_time_ms, unit: ' ms' },
      { key: 'p95_latency_ms', label: METRIC_LABELS.p95_latency_ms, value: perf.p95_latency_ms, unit: ' ms' },
      { key: 'lock_wait_ms', label: METRIC_LABELS.lock_wait_ms, value: mysql.innodb_row_lock_time_ms, unit: ' ms' },
      { key: 'deadlocks', label: METRIC_LABELS.deadlocks, value: mysql.deadlocks },
      { key: 'redo_latency_ms', label: METRIC_LABELS.redo_latency_ms, value: perf.redo_write_latency_ms, unit: ' ms' },
      { key: 'index_usage', label: METRIC_LABELS.index_usage, value: mysql.index_usage_rate, unit: '%' },
    ];
  }, [metrics]);

  // 高亮与常规指标分组，提升视觉层次
  const highlightKeys = ['cpu', 'mem', 'qps', 'p95_latency_ms'];
  const highlightItems = metricItems.filter(it => highlightKeys.includes(it.key));
  const restItems = metricItems.filter(it => !highlightKeys.includes(it.key));

  return (
    <div style={{ padding: 24 }}>
      {/* 操作条（与架构优化一致的风格） */}
      <Card className="content-card" style={{ marginBottom: 16, borderRadius: '18px' }}>
        <Space size={12} wrap>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontWeight: 600, color: '#1f1f1f', fontSize: 18 }}>
            <DatabaseOutlined style={{ color: '#722ED1', fontSize: 20 }} />
            选择实例
          </span>
          <Select
            showSearch
            placeholder="请选择实例"
            style={{ width: 380 }}
            value={selectedInstance || undefined}
            onChange={setSelectedInstance}
            filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
            options={instanceOptions}
          />
          <Button type="primary" loading={loading} onClick={handleAnalyze}>
            {loading ? '分析中...' : '分析'}
          </Button>
        </Space>
      </Card>

      {/* 指标与建议区域 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title={<span><LineChartOutlined style={{ marginRight: 8, color: '#1677ff' }} />核心性能指标</span>} style={{ borderRadius: '18px' }}>
            {/* 颜色含义提示区域 */}
            <div style={{ 
              marginBottom: 16, 
              padding: '12px 16px', 
              background: 'rgba(24, 144, 255, 0.04)', 
              border: '1px solid rgba(24, 144, 255, 0.15)', 
              borderRadius: 18,
              fontSize: 13
            }}>
              <div style={{ fontWeight: 600, marginBottom: 8, color: '#1677ff' }}>📊 指标状态说明</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ 
                    width: 12, 
                    height: 12, 
                    borderRadius: '50%', 
                    background: '#52c41a',
                    border: '2px solid rgba(82, 196, 26, 0.3)'
                  }}></div>
                  <span style={{ color: '#52c41a', fontWeight: 500 }}>正常</span>
                  <span style={{ color: '#8c8c8c' }}>健康范围</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ 
                    width: 12, 
                    height: 12, 
                    borderRadius: '50%', 
                    background: '#faad14',
                    border: '2px solid rgba(250, 173, 20, 0.4)'
                  }}></div>
                  <span style={{ color: '#faad14', fontWeight: 500 }}>警告</span>
                  <span style={{ color: '#8c8c8c' }}>需要关注</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ 
                    width: 12, 
                    height: 12, 
                    borderRadius: '50%', 
                    background: '#ff4d4f',
                    border: '2px solid rgba(255, 77, 79, 0.4)'
                  }}></div>
                  <span style={{ color: '#ff4d4f', fontWeight: 500 }}>异常</span>
                  <span style={{ color: '#8c8c8c' }}>立即处理</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ 
                    width: 12, 
                    height: 12, 
                    borderRadius: '50%', 
                    background: '#000000',
                    border: '2px solid rgba(0, 0, 0, 0.3)'
                  }}></div>
                  <span style={{ color: '#000000', fontWeight: 500 }}>默认</span>
                  <span style={{ color: '#8c8c8c' }}>中性指标</span>
                </div>
              </div>
            </div>
            
            {!metrics && loading && <Skeleton active paragraph={{ rows: 6 }} />}
            {metrics && (
              <div className="metrics-section">
                {/* 高亮指标：更大字号与卡片，突出核心关注项 */}
                <div className="metrics-grid highlight">
                  {highlightItems.map(it => (
                    <div key={it.key} className={`metric-tile ${getSeverity(it.key, it.value)}`}>
                      <div className="label">{it.label}</div>
                      <div className="value">{formatValue(it.value, it.unit || '')}</div>
                    </div>
                  ))}
                </div>
                {/* 其余指标：紧凑网格，信息密度更高 */}
                <div className="metrics-grid">
                  {restItems.map(it => (
                    <div key={it.key} className={`metric-tile small ${getSeverity(it.key, it.value)}`}>
                      <div className="label">{it.label}</div>
                      <div className="value">{formatValue(it.value, it.unit || '')}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {!loading && !metrics && (
              <Alert type="info" showIcon message="尚未加载指标" description="点击上方'分析'后，将展示核心性能指标。" style={{ marginTop: 8 }} />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card 
            title={
              <span style={{ 
                color: '#1890ff', 
                fontSize: '16px', 
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center'
              }}>
                <BulbOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                AI 配置建议
              </span>
            } 
            style={{ 
              borderRadius: '18px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
              border: '1px solid #e8f4ff'
            }}
            headStyle={{
              background: 'linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%)',
              borderRadius: '18px 18px 0 0',
              borderBottom: '1px solid #d6f7ff'
            }}
          >
            {adviceStatus === 'loading' && <Skeleton active paragraph={{ rows: 8 }} />}
            {adviceStatus !== 'loading' && (
              <AdviceCard text={advice} status={adviceStatus} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ConfigOptimization;
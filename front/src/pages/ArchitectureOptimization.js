import React, { useEffect, useState } from 'react';
import { Card, Select, Button, Space, Descriptions, Tag, Table, message, Divider, Tooltip, Alert } from 'antd';
import { DatabaseOutlined, BulbOutlined } from '@ant-design/icons';
import API_BASE_URL from '../config/api';
import apiClient from '../utils/apiClient';
import { useInstances } from '../contexts/InstanceContext';
import { formatAnalysis } from '../utils/analysisFormatter';
import { renderAnalysis } from '../utils/commonUtils';
import { useDebounceCallback } from '../hooks/useDebounce';

// 轻量 Markdown 清洗：兜底清洗代码围栏/强调/列表符等
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





const ArchitectureOptimization = () => {
  const [selectedInstance, setSelectedInstance] = useState('');
  const { getRunningInstanceOptions } = useInstances();
  const instanceOptions = getRunningInstanceOptions();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [overview, setOverview] = useState(null);
  const [replication, setReplication] = useState(null);
  const [riskItems, setRiskItems] = useState([]);
  const [slowData, setSlowData] = useState(null);
  const [isSlowAnalyzing, setIsSlowAnalyzing] = useState(false);
  const [llmAdviceText, setLlmAdviceText] = useState('');
  const [hasAnalyzed, setHasAnalyzed] = useState(false);
  // 如果需要错误状态，在这里添加
  const [llmAdviceError, setLlmAdviceError] = useState('');
  // 新增 DeepSeek 状态，修复 setDeepSeekStatus 未定义
  const [deepSeekStatus, setDeepSeekStatus] = useState('idle');

  // 当实例选择无效时重置
  useEffect(() => {
    if (selectedInstance && !instanceOptions.some(opt => opt.value === selectedInstance)) {
      setSelectedInstance('');
      setOverview(null);
      setReplication(null);
      setRiskItems([]);
      setLlmAdviceText('');
      setHasAnalyzed(false);
      message.warning('所选实例已不可用，选择已重置');
    }
  }, [selectedInstance, instanceOptions]);

  // 防抖的分析函数，避免用户快速点击时重复请求
  const debouncedAnalyze = useDebounceCallback(async () => {
    if (!selectedInstance) {
      message.warning('请先选择数据库实例');
      return;
    }
    
    setHasAnalyzed(true);
    setIsAnalyzing(true);
    
    try {
      const data = await apiClient.analyzeArchitecture(selectedInstance);
      
      // 处理基础数据
      setOverview(data.overview || null);
      setReplication(data.replication || null);
      setRiskItems(Array.isArray(data.risks) ? 
        data.risks.map((r, idx) => ({ key: r.key || `risk_${idx}`, ...r })) : []);
      
      // 简化DeepSeek数据处理
      handleDeepSeekResponse(data);
      
      message.success('架构检查完成');

      // 并行触发慢日志分析
      try {
        setIsSlowAnalyzing(true);
        const sdata = await apiClient.analyzeSlowlog(selectedInstance);
        setSlowData(sdata);
      } catch (e) {
        message.warning('慢日志分析失败');
        setSlowData(null);
      } finally {
        setIsSlowAnalyzing(false);
      }
      
    } catch (e) {
      console.error(e);
      message.error('架构检查失败');
    } finally {
      setIsAnalyzing(false);
    }
  }, 500, [selectedInstance]);

  const handleAnalyze = () => {
    // 调用防抖的分析函数
    debouncedAnalyze();
  };
  
  // 规范化 DeepSeek 返回：优先提取文本字段，其次安全字符串化
  const normalizeAdvice = (val) => {
    if (val == null) return '';
    if (typeof val === 'string') return val;
    if (typeof val === 'object') {
      if (typeof val.content === 'string') return val.content;
      if (typeof val.text === 'string') return val.text;
      if (typeof val.message === 'string') return val.message;
      try { return JSON.stringify(val); } catch { return String(val); }
    }
    return String(val);
  };

  // 净化文本：处理换行符、去除多余引号和大括号、压缩空行
  const sanitizeAdviceText = (text) => {
    if (!text || typeof text !== 'string') return '';
    
    return text
      .replace(/\\n/g, '\n')           // 还原转义的换行符
      .replace(/^["'{]+|["'}]+$/g, '') // 去除开头结尾的引号和大括号
      .replace(/\n\s*\n\s*\n/g, '\n\n') // 压缩多个连续空行为两个
      .replace(/^\s+|\s+$/g, '')       // 去除首尾空白
      .trim();
  };

  function handleDeepSeekResponse(data) {
    console.log('DeepSeek响应:', data.llm_advice, data.error);

    if (data.error) {
      // 有错误 - DeepSeek未连接
      setLlmAdviceText('');
      setDeepSeekStatus('error');
    } else if (data.llm_advice) {
      // 有内容 - DeepSeek正常（做规范化和净化处理）
      const rawText = normalizeAdvice(data.llm_advice);
      const cleanText = sanitizeAdviceText(rawText);
      setLlmAdviceText(cleanText);
      setDeepSeekStatus('success');
    } else {
      // 无内容无错误 - DeepSeek连接但无建议
      setLlmAdviceText('');
      setDeepSeekStatus('empty');
    }
  }

  const columns = [
    { title: '类别', dataIndex: 'category', key: 'category', width: 160, render: (t) => <Tag>{t}</Tag> },
    { title: '项目', dataIndex: 'item', key: 'item', width: 200 },
    { title: '当前值', dataIndex: 'current', key: 'current', width: 240, render: (t) => (
      <code style={{ backgroundColor: '#f5f5f5', padding: '2px 6px', borderRadius: 18 }}>{t}</code>
    ) },
    { title: '风险等级', dataIndex: 'level', key: 'level', width: 120, render: (l) => (
      <Tag color={statusColor(l)}>{l === 'error' ? '高' : l === 'warning' ? '中' : '低'}</Tag>
    ) },
    { title: '建议', dataIndex: 'recommendation', key: 'recommendation' },
  ];

  // 概览展示顺序（含新增项）
  const overviewOrder = [
    'log_bin', 'binlog_format', 'gtid_mode', 'enforce_gtid_consistency',
    'read_only', 'super_read_only', 'rpl_semi_sync_master_enabled', 'rpl_semi_sync_slave_enabled',
    'sync_binlog', 'innodb_flush_log_at_trx_commit',
    'binlog_row_image', 'binlog_expire_logs_seconds', 'master_info_repository', 'relay_log_info_repository',
  ];

  const renderOverviewValue = (k, v) => {
    const key = String(k);
    const up = String(v ?? '').toUpperCase();
    if (['log_bin', 'read_only', 'super_read_only', 'rpl_semi_sync_master_enabled', 'rpl_semi_sync_slave_enabled'].includes(key)) {
      return renderStatusTag(v);
    }
    if (['io_thread', 'sql_thread'].includes(key)) return renderStatusTag(v);
    if (['N/A', 'UNKNOWN', ''].includes(up)) return (
      <Tooltip title="该指标暂无数据或不适用。可能原因：1）参数未支持或未启用；2）当前实例角色/版本不适用；3）临时性超时或权限不足导致采集失败。">
        <Tag>{v ?? 'N/A'}</Tag>
      </Tooltip>
    );
    return <Tag color="blue">{String(v)}</Tag>;
  };

  // 复制状态字段顺序（含新增项）
  const replOrder = [
    'seconds_behind', 'io_thread', 'sql_thread', 'Replica_SQL_Running_State',
    'Executed_Gtid_Set', 'Retrieved_Gtid_Set', 'Last_Error',
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* 操作条 */}
      <Card className="content-card" style={{ marginBottom: 16, borderRadius: '18px' }}>
        <Space size={12} wrap>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontWeight: 600, color: '#1f1f1f', fontSize: 18, letterSpacing: 0.2 }}>
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
          <Button type="primary" loading={isAnalyzing} onClick={handleAnalyze}>
            {isAnalyzing ? '分析中...' : '开始架构检查'}
          </Button>
        </Space>
      </Card>

      {/* 概览 */}
      <Card className="content-card" style={{ marginBottom: 16, borderRadius: '18px' }} bordered>
        {!overview ? (
          <div style={{ color: '#8c8c8c' }}>请先选择实例并点击“开始架构检查”。</div>
        ) : (
          <>
            <Descriptions column={3} size="middle" bordered>
              {overviewOrder.filter((k) => overview[k] !== undefined).map((k) => (
                <Descriptions.Item key={k} label={renderMixedLabel(k)}>
                  {renderOverviewValue(k, overview[k])}
                </Descriptions.Item>
              ))}
            </Descriptions>
            {replication && replication.is_replica ? (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Descriptions title="复制状态" column={2} size="middle" bordered>
                  {replOrder.filter((k) => replication[k] !== undefined).map((k) => (
                    <Descriptions.Item key={k} label={renderMixedLabel(k)}>
                      {renderOverviewValue(k, replication[k])}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </>
            ) : (
              <div style={{ color: '#8c8c8c', marginTop: 8 }}>未检测到从库复制状态。</div>
            )}
          </>
        )}
      </Card>

      {/* 新增：AI 架构建议（复用 SQL 审核优化的渲染） */}
      {(isAnalyzing || hasAnalyzed) && (
        <Card
          className="content-card"
          title={
            <span style={{ 
              color: '#1890ff', 
              fontSize: '16px', 
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center'
            }}>
              <BulbOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              AI 架构建议
            </span>
          }
          style={{ 
            marginBottom: 16, 
            borderRadius: '18px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            border: '1px solid #e8f4ff'
          }}
          headStyle={{
            background: 'linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%)',
            borderRadius: '18px 18px 0 0',
            borderBottom: '1px solid #91d5ff'
          }}
          bordered
        >
          {isAnalyzing ? (
            <Alert
              message="正在分析中..."
              description="正在获取架构分析结果，请稍候。"
              type="info"
              showIcon
              style={{ marginBottom: 0 }}
            />
          ) : llmAdviceText ? (
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
                  架构优化建议与分析
                </span>
              }
              description={renderAnalysis(llmAdviceText)}
              type="info"
              showIcon={false}
              style={{ 
                marginBottom: 0,
                borderRadius: '12px',
                border: '1px solid #e8f4ff',
                background: 'linear-gradient(135deg, #fafcff 0%, #f0f9ff 100%)'
              }}
            />
          ) : hasAnalyzed ? (
            <Alert
              message="暂未获取到 DeepSeek 架构建议"
              description="架构检查已完成，但未获取到AI建议。已展示基础风险项分析结果。"
              type="info"
              showIcon
              style={{ marginBottom: 0 }}
            />
          ) : null}
        </Card>
      )}

      {/* 风险与建议 */}
      <Card className="content-card" title="风险与建议" style={{ borderRadius: '18px' }} bordered>
        <Table
          size="middle"
          rowKey="key"
          columns={columns}
          dataSource={riskItems}
          pagination={{ pageSize: 8 }}
        />
      </Card>

      {/* 慢查询分析 */}
      <Card className="content-card" title="慢查询分析" style={{ marginTop: 16, borderRadius: '18px' }} bordered extra={isSlowAnalyzing ? <Tag color="processing">分析中</Tag> : null}>
        {!slowData ? (
          <div style={{ color: '#8c8c8c' }}>尚无慢日志分析结果。请先点击“开始架构检查”。</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16 }}>
            <Descriptions size="small" column={3} bordered>
              <Descriptions.Item label="performance_schema">{slowData.overview?.performance_schema || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="slow_query_log">{slowData.overview?.slow_query_log || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="long_query_time">{String(slowData.overview?.long_query_time ?? 'N/A')}</Descriptions.Item>
              <Descriptions.Item label="log_output">{slowData.overview?.log_output || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="slow_log_file" span={2}><code>{slowData.overview?.slow_query_log_file || 'N/A'}</code></Descriptions.Item>
            </Descriptions>

            {Array.isArray(slowData.warnings) && slowData.warnings.length > 0 && (
              <Alert type="warning" showIcon message={slowData.warnings.join('；')} />
            )}

            <div>
              <h3 style={{ marginBottom: 8 }}>Top SQL 指纹（来自 performance_schema）</h3>
              <Table
                size="small"
                rowKey={(r) => r.digest + r.schema}
                dataSource={slowData.ps_top || []}
                pagination={{ pageSize: 8 }}
                columns={[
                  { title: 'Schema', dataIndex: 'schema', key: 'schema', width: 120 },
                  { title: '指纹', dataIndex: 'query', key: 'query', ellipsis: true },
                  { title: '次数', dataIndex: 'count', key: 'count', width: 80 },
                  { title: '平均耗时(ms)', dataIndex: 'avg_latency_ms', key: 'avg_latency_ms', width: 140 },
                  { title: '总耗时(ms)', dataIndex: 'total_latency_ms', key: 'total_latency_ms', width: 140 },
                  { title: 'RowsExamined(avg)', dataIndex: 'rows_examined_avg', key: 'rows_examined_avg', width: 160 },
                  { title: 'RowsSent(avg)', dataIndex: 'rows_sent_avg', key: 'rows_sent_avg', width: 140 },
                ]}
              />
            </div>

            <div>
              <h3 style={{ marginBottom: 8 }}>慢日志表抽样（最近记录）</h3>
              <Table
                size="small"
                rowKey={(r, idx) => String(idx)}
                dataSource={slowData.file_samples || []}
                pagination={{ pageSize: 5 }}
                columns={[
                  { title: '时间', dataIndex: 'time', key: 'time', width: 180 },
                  { title: 'DB', dataIndex: 'db', key: 'db', width: 120 },
                  { title: '查询耗时(ms)', dataIndex: 'query_time_ms', key: 'query_time_ms', width: 140 },
                  { title: '锁等待(ms)', dataIndex: 'lock_time_ms', key: 'lock_time_ms', width: 120 },
                  { title: 'Rows_sent', dataIndex: 'rows_sent', key: 'rows_sent', width: 100 },
                  { title: 'Rows_examined', dataIndex: 'rows_examined', key: 'rows_examined', width: 120 },
                  { title: 'SQL', dataIndex: 'sql', key: 'sql', ellipsis: true },
                ]}
              />
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ArchitectureOptimization;

// 辅助：风险等级颜色、标签翻译与渲染
const statusColor = (level) => {
  switch (level) {
    case 'error': return 'red';
    case 'warning': return 'orange';
    case 'success': return 'green';
    default: return 'default';
  }
};

// 英文参数 -> 中文翻译（用于概览与复制状态）
const OVERVIEW_LABELS = {
  log_bin: '二进制日志开关',
  binlog_format: 'Binlog 格式',
  gtid_mode: 'GTID 模式',
  enforce_gtid_consistency: '强制 GTID 一致性',
  read_only: '只读 (全局)',
  super_read_only: '超级只读',
  rpl_semi_sync_master_enabled: '半同步(主)',
  rpl_semi_sync_slave_enabled: '半同步(从)',
  sync_binlog: 'Binlog 同步策略',
  innodb_flush_log_at_trx_commit: '事务提交刷新策略',
  // 新增采集信号
  binlog_row_image: 'Binlog 行镜像',
  binlog_expire_logs_seconds: 'Binlog 保留时长(秒)',
  master_info_repository: 'Master 信息存储',
  relay_log_info_repository: 'RelayLog 信息存储',
};

const REPL_LABELS = {
  seconds_behind: '复制延迟(秒)',
  io_thread: 'IO 线程',
  sql_thread: 'SQL 线程',
  Replica_SQL_Running_State: 'SQL线程运行状态',
  Executed_Gtid_Set: '已执行 GTID 集合',
  Retrieved_Gtid_Set: '已获取 GTID 集合',
  Last_Error: '最后错误',
};

// 中英混排标签渲染：英文保持原样，中文放入全角括号
const englishLabelStyle = { fontFamily: 'Segoe UI, Roboto, Helvetica, Arial, sans-serif', fontWeight: 600, color: '#1f1f1f' };
const chineseLabelStyle = { fontFamily: '"Noto Sans SC", "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif', fontWeight: 400, color: '#8c8c8c', marginLeft: 4 };
const renderMixedLabel = (key) => {
  const cn = OVERVIEW_LABELS[key] || REPL_LABELS[key];
  return (
    <span>
      <span style={englishLabelStyle}>{key}</span>
      {cn ? <span style={chineseLabelStyle}>（{cn}）</span> : null}
    </span>
  );
};

// 用于给 ON/OFF、Yes/No 值上色
const renderStatusTag = (val) => {
  const s = String(val ?? '').toUpperCase();
  if (['ON', 'YES'].includes(s)) return <Tag color="green">{s}</Tag>;
  if (['OFF', 'NO'].includes(s)) return <Tag color="red">{s}</Tag>;
  if (s === 'N/A' || s === 'UNKNOWN' || s === '') return (
    <Tooltip title="该指标暂无数据或不适用。可能原因：1）参数未支持或未启用；2）当前实例角色/版本不适用；3）临时性超时或权限不足导致采集失败。">
      <Tag>{val ?? 'N/A'}</Tag>
    </Tooltip>
  );
  return <Tag color="blue">{val}</Tag>;
};

// 简化的渲染函数
const renderSimpleAnalysis = (text) => {
  if (!text) return null;
  
  // 按段落分割
  const paragraphs = text.split('\n\n').filter(p => p.trim());
  
  return (
    <div style={{ lineHeight: 1.6 }}>
      {paragraphs.map((paragraph, index) => {
        const lines = paragraph.split('\n').filter(line => line.trim());
        const title = lines[0];
        const content = lines.slice(1);
        
        return (
          <div key={index} style={{ marginBottom: 16 }}>
            {title.includes('【') && title.includes('】') ? (
              <>
                <h4 style={{ color: '#1890ff', marginBottom: 8 }}>{title}</h4>
                <div style={{ paddingLeft: 16 }}>
                  {content.map((line, i) => (
                    <div key={i} style={{ marginBottom: 4 }}>
                      {line.startsWith('- ') ? (
                        <span>• {line.substring(2)}</span>
                      ) : (
                        <span>{line}</span>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div>{paragraph}</div>
            )}
          </div>
        );
      })}
    </div>
  );
};

// 简化的状态显示
const renderDeepSeekCard = () => {
  if (deepSeekStatus === 'error') {
    return (
      <Alert
        message="DeepSeek 未连接"
        description="DeepSeek服务未配置或连接失败，显示基础规则分析结果"
        type="warning"
        showIcon
      />
    );
  }
  
  if (deepSeekStatus === 'success' && llmAdviceText) {
    return (
      <Alert
        message="DeepSeek 智能分析"
        description={renderSimpleAnalysis(llmAdviceText)}
        type="info"
        showIcon
      />
    );
  }
  
  return (
    <Alert
      message="DeepSeek 已连接"
      description="DeepSeek服务正常，但本次未返回具体建议"
      type="info"
      showIcon
    />
  );
};
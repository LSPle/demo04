import React, { useState, useEffect } from 'react';
import { Card, Select, Input, Button, Alert, message, Typography } from 'antd';
import {
  DatabaseOutlined,
  CodeOutlined,
  BulbOutlined
} from '@ant-design/icons';
import apiClient from '../utils/apiClient';
import { useInstances } from '../contexts/InstanceContext';
import { formatAnalysis, getHighlightKeywords } from '../utils/analysisFormatter';

const { TextArea } = Input;
const { Option } = Select;
const { Paragraph } = Typography;

// 智能渲染：将纯文本分析格式化为带小节与要点的列表，并高亮关键字
const renderAnalysis = (text) => {
  const { sections } = formatAnalysis(text);
  const keywords = getHighlightKeywords();
  const highlight = (str) => {
    if (!str) return str;
    let out = String(str);
    // 简单高亮：将关键词包裹标记
    keywords.forEach(k => {
      const esc = k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      out = out.replace(new RegExp(esc, 'g'), (m) => `$$$HL${m}$$$`);
    });
    // 转成 React 片段
    const parts = out.split(/\$\$\$HL/);
    const nodes = [];
    parts.forEach((p, idx) => {
      const endIdx = p.indexOf('$$$');
      if (endIdx >= 0) {
        const word = p.slice(0, endIdx);
        const rest = p.slice(endIdx + 3);
        nodes.push(<span key={`hl-${idx}`} style={{ background: 'rgba(250, 173, 20, 0.2)', padding: '0 2px' }}>{word}</span>);
        if (rest) nodes.push(<span key={`t-${idx}`}>{rest}</span>);
      } else {
        nodes.push(<span key={`p-${idx}`}>{p}</span>);
      }
    });
    return <>{nodes}</>;
  };

  return (
    <div className="analysis-text" style={{ lineHeight: 1.7 }}>
      {sections.map((sec, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{sec.title}</div>
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            {sec.items.map((it, j) => (
              <li key={j} style={{ marginBottom: 4 }}>{highlight(it)}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

const SQLOptimization = () => {
  const [selectedInstance, setSelectedInstance] = useState('');
  const [selectedDatabase, setSelectedDatabase] = useState('');
  const [sqlQuery, setSqlQuery] = useState('');
  const [optimizationResults, setOptimizationResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // 数据库实例选项
  const { getRunningInstanceOptions } = useInstances();
  const instanceOptions = getRunningInstanceOptions();
  // 数据库选项
  const [databaseOptions, setDatabaseOptions] = useState([]);
  const [loadingDatabases, setLoadingDatabases] = useState(false);

  // 当实例选择无效时重置
  useEffect(() => {
    if (selectedInstance && !instanceOptions.some(opt => opt.value === selectedInstance)) {
      setSelectedInstance('');
      message.warning('所选实例已不可用，选择已重置');
    }
  }, [selectedInstance, instanceOptions]);

  // 当选择实例时，获取该实例的数据库列表
  useEffect(() => {
    if (selectedInstance) {
      fetchDatabases(selectedInstance);
    } else {
      setDatabaseOptions([]);
      setSelectedDatabase('');
    }
  }, [selectedInstance]);

  const fetchDatabases = async (instanceId) => {
    setLoadingDatabases(true);
    try {
      const data = await apiClient.getInstanceDatabases(instanceId);
      const databases = data.databases || [];
      setDatabaseOptions(databases.map(db => ({ value: db, label: db })));
      
      // 如果只有一个数据库，自动选择
      if (databases.length === 1) {
        setSelectedDatabase(databases[0]);
      } else {
        setSelectedDatabase('');
      }
    } catch (err) {
      console.error('获取数据库列表失败:', err);
      message.error('获取数据库列表失败，请检查实例连接状态');
      setDatabaseOptions([]);
    } finally {
      setLoadingDatabases(false);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedInstance) {
      message.warning('请选择实例');
      return;
    }
    if (!selectedDatabase) {
      message.warning('请选择数据库');
      return;
    }
    if (!sqlQuery.trim()) {
      message.warning('请输入SQL语句');
      return;
    }

    setIsAnalyzing(true);
    try {
      const payload = { 
        instanceId: Number(selectedInstance), 
        sql: sqlQuery.trim(),
        database: selectedDatabase
      };

      const data = await apiClient.analyzeSql(payload);
      const analysis = data?.analysis || null;
      
      setOptimizationResults({
        originalQuery: sqlQuery,
        analysis
      });
    } catch (e) {
      console.error(e);
      message.error(`分析失败：${e.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleReset = () => {
    setSelectedInstance('');
    setSelectedDatabase('');
    setSqlQuery('');
    setOptimizationResults(null);
    setDatabaseOptions([]);
  };

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <div className="page-header">
        <h1>SQL审核优化</h1>
        <p>选择实例和数据库，对SQL语句进行审核优化</p>
      </div>

      {/* 主要内容区域 */}
      <Card className="content-card">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          
          {/* 实例选择 */}
          <div>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              数据库实例 <span style={{ color: '#ff4d4f' }}>*</span>
            </label>
            <Select
              placeholder="请选择数据库实例"
              style={{ width: '100%' }}
              value={selectedInstance}
              onChange={setSelectedInstance}
              notFoundContent="暂无可用实例"
            >
              {instanceOptions.map(option => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
          </div>

          {/* 数据库选择 */}
          {selectedInstance && (
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
                <CodeOutlined style={{ marginRight: 8 }} />
                数据库 <span style={{ color: '#ff4d4f' }}>*</span>
              </label>
              <Select
                placeholder={loadingDatabases ? "正在加载数据库列表..." : "请选择数据库"}
                style={{ width: '100%' }}
                value={selectedDatabase}
                onChange={setSelectedDatabase}
                loading={loadingDatabases}
                notFoundContent={loadingDatabases ? "加载中..." : "暂无可用数据库"}
              >
                {databaseOptions.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
              <div style={{ marginTop: 4, color: '#8c8c8c', fontSize: 12 }}>
                选择数据库可以提供更精确的优化建议
              </div>
            </div>
          )}

          {/* SQL输入 */}
          <div>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
              SQL 语句 <span style={{ color: '#ff4d4f' }}>*</span>
            </label>
            <TextArea
              rows={6}
              placeholder="请输入需要分析的SQL语句"
              value={sqlQuery}
              onChange={(e) => setSqlQuery(e.target.value)}
            />
            <div style={{ marginTop: 4, color: '#8c8c8c', fontSize: 12 }}>
              支持SELECT/INSERT/UPDATE/DELETE等语句
            </div>
          </div>

          {/* 操作按钮 */}
          <div style={{ display: 'flex', gap: 12 }}>
            <Button type="primary" onClick={handleAnalyze} loading={isAnalyzing}>
              开始分析
            </Button>
            <Button onClick={handleReset} disabled={isAnalyzing}>重置</Button>
          </div>

          {/* 分析结果 */}
          {optimizationResults && (
            <Card type="inner" title={<span><BulbOutlined style={{ marginRight: 8 }} />分析结果</span>}
                  style={{ marginTop: 16 }}>
              {optimizationResults.analysis ? (
                <Alert
                  className="analysis-alert"
                  message="分析与建议"
                  description={renderAnalysis(optimizationResults.analysis)}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              ) : (
                <Alert message="分析服务不可用" description="DeepSeek API 未配置或服务暂时不可用，请联系管理员配置 API 密钥" type="warning" showIcon style={{ marginBottom: 16 }} />
              )}

              {/* 移除建议SQL展示 */}
            </Card>
          )}
        </div>
      </Card>
    </div>
  );
};

export default SQLOptimization;
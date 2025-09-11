import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Space, Button, message } from 'antd';
import {
  DatabaseOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  WifiOutlined
} from '@ant-design/icons';
import { API_ENDPOINTS } from '../config/api';
import websocketService from '../services/websocketService';

const InstanceOverview = () => {
  // 状态管理
  const [instanceData, setInstanceData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statsData, setStatsData] = useState([
    {
      title: '总实例数',
      value: 0,
      color: '#1890ff',
      icon: <DatabaseOutlined />
    },
    {
      title: '运行中',
      value: 0,
      color: '#52c41a',
      icon: <PlayCircleOutlined />
    },
    {
      title: '异常实例',
      value: 0,
      color: '#ff4d4f',
      icon: <ExclamationCircleOutlined />
    }
  ]);
  
  const [wsConnected, setWsConnected] = useState(false);



  // 从后端获取实例数据（包含实时指标）
  const fetchInstanceData = async () => {
    try {
      setLoading(true);
      const response = await fetch(API_ENDPOINTS.INSTANCES);
      if (!response.ok) throw new Error('API响应失败');
      const data = await response.json();
      processInstanceData(data);
    } catch (error) {
      console.error('获取实例数据失败:', error);
      message.error('获取实例数据失败，请检查后端服务');
      
      // 当API获取失败时，如果有现有数据则设置为已关闭状态，否则设置为空数组
      if (instanceData.length > 0) {
        const closedInstances = instanceData.map(instance => ({
          ...instance,
          status: 'closed'
        }));
        setInstanceData(closedInstances);
        updateStatsData(closedInstances);
      } else {
        setInstanceData([]);
        updateStatsData([]);
      }
    } finally {
      setLoading(false);
    }
  };

  // 刷新实例状态
  const refreshInstanceStatus = async () => {
    try {
      setLoading(true);
      message.loading('正在检测实例状态...', 0);
      
      // 调用后端状态检测接口
      const response = await fetch(API_ENDPOINTS.MONITOR_CHECK, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) throw new Error('状态检测失败');
      const result = await response.json();
      
      message.destroy();
      message.success(`状态检测完成：总数${result.total}，正常${result.normal}，异常${result.error}`);
      
      // 重新获取实例数据
      await fetchInstanceData();
    } catch (error) {
      message.destroy();
      console.error('刷新实例状态失败:', error);
      message.error('刷新实例状态失败，请检查后端服务');
    } finally {
      setLoading(false);
    }
  };

  // 处理实例数据
  const processInstanceData = (data) => {
    // 转换后端数据格式以匹配前端展示需求
    const formattedData = data.map(instance => ({
      key: instance.id,
      name: instance.instanceName,
      ip: `${instance.host}:${instance.port}`,
      type: instance.dbType,
      status: instance.status,
      connectionInfo: {
        host: instance.host,
        port: instance.port,
        username: instance.username,
        password: instance.password
      }
    }));
    
    setInstanceData(formattedData);
    
    // 更新统计数据
    updateStatsData(formattedData);
  };

  // 更新统计数据
  const updateStatsData = (instances) => {
    const totalCount = instances.length;
    const runningCount = instances.filter(item => item.status === 'running').length;
    const errorCount = instances.filter(item => item.status === 'error' || item.status === 'closed').length;

    setStatsData(prevStats => prevStats.map((stat, index) => {
      const values = [totalCount, runningCount, errorCount];
      return {
        ...stat,
        value: values[index]
      };
    }));
  };

  // WebSocket事件处理
  useEffect(() => {
    // 连接WebSocket
    websocketService.connect();
    
    // 监听连接状态变化
    const handleConnectionChange = () => {
      const status = websocketService.getConnectionStatus();
      setWsConnected(status.isConnected);
    };
    
    // 监听实例状态变化
    const handleInstanceStatusChange = (data) => {
      console.log('收到实例状态变化:', data);
      message.info(`实例 ${data.name} 状态变更为: ${data.status === 'running' ? '运行中' : '异常'}`);
      
      // 更新单个实例状态
      setInstanceData(prevData => 
        prevData.map(instance => 
          instance.key === data.id 
            ? { ...instance, status: data.status }
            : instance
        )
      );
    };
    
    // 监听状态汇总更新
    const handleStatusSummaryUpdate = (data) => {
      console.log('收到状态汇总更新:', data);
      setStatsData(prevStats => prevStats.map((stat, index) => {
        const values = [data.total, data.running, data.error];
        return {
          ...stat,
          value: values[index]
        };
      }));
    };
    
    // 监听所有实例状态更新
    const handleInstancesStatusUpdate = (data) => {
      console.log('收到所有实例状态更新:', data);
      if (data.instances) {
        const formattedData = data.instances.map(instance => ({
          key: instance.id,
          name: instance.name,
          ip: `${instance.host}:${instance.port}`,
          type: instance.dbType || 'MySQL',
          status: instance.status,
          connectionInfo: {
            host: instance.host,
            port: instance.port
          }
        }));
        setInstanceData(formattedData);
      }
      
      if (data.summary) {
        handleStatusSummaryUpdate(data.summary);
      }
    };
    
    // 注册事件监听器
    websocketService.on('instanceStatusChange', handleInstanceStatusChange);
    websocketService.on('statusSummaryUpdate', handleStatusSummaryUpdate);
    websocketService.on('instancesStatusUpdate', handleInstancesStatusUpdate);
    
    // 初始获取数据
    fetchInstanceData();
    
    // 定期检查连接状态
    const statusInterval = setInterval(handleConnectionChange, 1000);
    
    // 清理函数
    return () => {
      clearInterval(statusInterval);
      websocketService.off('instanceStatusChange', handleInstanceStatusChange);
      websocketService.off('statusSummaryUpdate', handleStatusSummaryUpdate);
      websocketService.off('instancesStatusUpdate', handleInstancesStatusUpdate);
      // 注意：不在这里断开WebSocket连接，因为其他组件可能也在使用
    };
  }, []);

  

  const getStatusTag = (status) => {
    const statusMap = {
      running: { color: 'success', text: '运行中' },
      warning: { color: 'warning', text: '警告' },
      error: { color: 'error', text: '异常' },
      closed: { color: 'default', text: '已关闭' }
    };
    const config = statusMap[status] || { color: 'default', text: '未知' };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: '实例名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
      width: 150,
    },
    {
      title: '数据库类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => getStatusTag(status),
    },
  ];

  return (
    <div className="fade-in-up">
      {/* 页面标题 */}
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>实例概览</h1>
            <p>数据库实例运行状态总览</p>
          </div>
          <Space>
            {/* WebSocket连接状态指示器 */}
            <Tag 
              color={wsConnected ? 'success' : 'error'} 
              icon={<WifiOutlined />}
              style={{ marginRight: 8 }}
            >
              {wsConnected ? '实时连接' : '连接断开'}
            </Tag>
            <Button 
              type="primary" 
              icon={<ReloadOutlined />} 
              onClick={refreshInstanceStatus}
              loading={loading}
            >
              刷新状态
            </Button>
          </Space>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="stats-grid">
        {statsData.map((stat, index) => {
          const cardClass = stat.color === '#52c41a' ? 'success' : 
                           stat.color === '#faad14' ? 'warning' : 
                           stat.color === '#ff4d4f' ? 'error' : '';
          return (
            <div 
              key={index} 
              className={`stat-card ${cardClass} fade-in-up`}
              style={{
                animationDelay: `${index * 0.1}s`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: 14, color: '#8c8c8c', marginBottom: 8 }}>
                    {stat.title}
                  </div>
                  <div style={{ 
                    fontSize: 32, 
                    fontWeight: 700, 
                    color: stat.color, 
                    marginBottom: 8,
                    textShadow: '0 2px 4px rgba(0,0,0,0.1)'
                  }}>
                    {stat.value}
                  </div>
                </div>
                <div style={{ 
                  fontSize: 28, 
                  color: stat.color,
                  background: `${stat.color}15`,
                  padding: '12px',
                  borderRadius: '12px',
                  transition: 'all 0.3s ease'
                }}>
                  {stat.icon}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 数据库实例列表 */}
      <Card
        title="数据库实例列表"
        className="content-card fade-in-up"
        style={{
          animationDelay: '0.4s'
        }}
      >
        <Table
          columns={columns}
          dataSource={instanceData}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
          }}
          rowClassName={(record, index) => `fade-in-up`}
          style={{
            '--animation-delay': '0.6s'
          }}
        />
      </Card>
    </div>
  );
};

export default InstanceOverview;
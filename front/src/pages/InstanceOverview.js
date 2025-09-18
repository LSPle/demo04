import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Tag, Button, message } from 'antd';
import {
  DatabaseOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import websocketService from '../services/websocketService';
import instanceService from '../services/instanceService';

const InstanceOverview = () => {
  // 基础状态管理
  const [loading, setLoading] = useState(false);
  const [instances, setInstances] = useState([]);
  
  // 直接在组件中计算统计数据
  const { totalCount, runningCount, errorCount } = useMemo(() => {
    if (!Array.isArray(instances)) {
      return { totalCount: 0, runningCount: 0, errorCount: 0 };
    }
    
    const totalCount = instances.length;
    const runningCount = instances.filter(item => item.status === 'running').length;
    const errorCount = instances.filter(item => 
      item.status === 'error' || item.status === 'closed'
    ).length;
    
    return { totalCount, runningCount, errorCount };
  }, [instances]);

  // 获取实例列表
  const fetchInstances = async () => {
    try {
      setLoading(true);
      const instanceList = await instanceService.fetchInstances();
      setInstances(instanceList);
    } catch (error) {
      console.error('获取实例列表失败:', error);
      message.error('获取实例列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 刷新实例状态
  const refreshInstanceStatus = async () => {
    try {
      setLoading(true);
      message.loading('正在检测实例状态...', 0);
      const result = await instanceService.refreshInstanceStatus();
      message.destroy();
      message.success(`状态检测完成：总数${result.total}，正常${result.normal}，异常${result.error}`);
      // 重新获取实例列表
      await fetchInstances();
    } catch (error) {
      message.destroy();
      console.error('刷新实例状态失败:', error);
      message.error('刷新实例状态失败，请检查后端服务');
    } finally {
      setLoading(false);
    }
  };

  // 页面加载时获取数据
  useEffect(() => {
    fetchInstances();
  }, []);


  // WebSocket连接和实时更新
  useEffect(() => {
    // 连接WebSocket
    websocketService.connect();

    // 监听连接状态变化
    websocketService.on('connected', () => {
      console.log('WebSocket已连接');
    });

    websocketService.on('disconnected', () => {
      console.log('WebSocket已断开');
    });

    // 监听实例状态更新
    websocketService.on('instances_status_update', (data) => {
      console.log('收到实例状态更新:', data);
      if (data && Array.isArray(data.instances)) {
        setInstances(data.instances);
      }
    });

    // 监听单个实例状态变化
    websocketService.on('instance_status_change', (data) => {
      console.log('收到单个实例状态变化:', data);
      if (data && data.instance) {
        setInstances(prevInstances =>
          prevInstances.map(instance =>
            instance.id === data.instance.id
              ? { ...instance, status: data.instance.status }
              : instance
          )
        );
      }
    });

    // 清理函数
    return () => {
      websocketService.disconnect();
    };
  }, []);

  // 状态标签显示
  const getStatusTag = (status) => {
    if (status === 'running') {
      return <Tag color="green">运行中</Tag>;
    } else if (status === 'error') {
      return <Tag color="red">异常</Tag>;
    } else if (status === 'closed') {
      return <Tag color="red">已关闭</Tag>;
    } else {
      return <Tag color="gray">未知</Tag>;
    }
  };

  // 表格列配置
  const columns = [
    {
      title: '实例名称',
      dataIndex: 'instanceName',
      key: 'instanceName',
      width: 200,
    },
    {
      title: '连接地址',
      key: 'address',
      width: 150,
      render: (_, record) => {
        return `${record.host}:${record.port}`;
      },
    },
    {
      title: '数据库类型',
      dataIndex: 'dbType',
      key: 'dbType',
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

  // 统计卡片数据
  const statsCards = [
    {
      title: '总实例数',
      value: totalCount,
      color: '#1890ff',
      icon: <DatabaseOutlined />,
      cardClass: 'stat-card'
    },
    {
      title: '运行中',
      value: runningCount,
      color: '#52c41a',
      icon: <PlayCircleOutlined />,
      cardClass: 'stat-card success'
    },
    {
      title: '异常实例',
      value: errorCount,
      color: '#ff4d4f',
      icon: <ExclamationCircleOutlined />,
      cardClass: 'stat-card error'
    }
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
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={refreshInstanceStatus}
            loading={loading}
          >
            刷新状态
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="stats-grid">
        {statsCards.map((stat, index) => (
          <div key={index} className={stat.cardClass}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="stat-number" style={{ color: stat.color }}>
                  {stat.value}
                </div>
                <div style={{
                  fontSize: '14px',
                  color: '#8c8c8c',
                  fontWeight: '500',
                  marginTop: '4px'
                }}>
                  {stat.title}
                </div>
              </div>
              <div style={{
                fontSize: '32px',
                color: stat.color,
                opacity: 0.8,
                marginLeft: '16px'
              }}>
                {stat.icon}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 数据库实例列表 */}
      <Card className="content-card" style={{ borderRadius: '18px' }}>
        <Table
          columns={columns}
          dataSource={instances}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `显示 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
          }}
        />
      </Card>
    </div>
  );
};

export default InstanceOverview;
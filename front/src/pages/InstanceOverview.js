import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Tag, Button, message, Space } from 'antd';
import {
  DatabaseOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import websocketService from '../services/websocketService';
import instanceService from '../services/instanceService';

const InstanceOverview = () => {
  // 1. 状态管理
  const [loading, setLoading] = useState(false);
  const [instances, setInstances] = useState([]);
  
  // 2. 计算属性
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

  // 3. 渲染辅助函数
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

  // 4. 渲染配置（依赖辅助函数）
  const columns = [
    {
      title: '实例名称',
      dataIndex: 'instanceName',
      key: 'instanceName',
      width: 200,
      render: (text, record) => (
        <Space>
          <DatabaseOutlined style={{ color: '#1890ff' }} />
          <span style={{ fontWeight: 500 }}>{text}</span>
        </Space>
      ),
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

  // 5. 业务逻辑函数
  // 获取实例列表
  const fetchInstances = async () => {
    try {
      setLoading(true);
      const instanceList = await instanceService.fetchInstances();
      console.log('获取到的实例列表:', instanceList);
      
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
      message.loading('正在检测实例状态...', 0);  //0表示持续时间
      const result = await instanceService.refreshInstanceStatus();
      message.destroy();  //关闭加载提示
      message.success(`状态检测完成：总数${result.total}，正常${result.normal}，异常${result.error}`);
      // 重新获取实例列表，强制等待完成
      await fetchInstances(); 
    } catch (error) {
      message.destroy();
      console.error('刷新实例状态失败:', error);
      message.error('刷新实例状态失败，请检查后端服务');
    } finally {
      setLoading(false);
    }
  };

  // 6. userEffect（依赖业务函数）
  useEffect(() => {
    fetchInstances();
  }, []);

  useEffect(() => {
    // WebSocket logic
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

    // 监听单个实例状态变化，指定数据名'instance_status_change'
    websocketService.on('instance_status_change', (receivedData) => {
      // console.log('收到单个实例状态变化:', receivedData);
      
      // 检查接收到的数据是否有效
      if (!receivedData || !receivedData.instance) {
        console.warn('接收到的实例数据无效');
        return;
      }
      
      // 实现实例状态的实时更新
      const updatedInstance = receivedData.instance;
      setInstances(currentInstances => {
        return currentInstances.map(instance => {
          // 如果是要更新的实例，则更新其状态
          if (instance.id === updatedInstance.id) {
            return {
              ...instance,
              status: updatedInstance.status
            };
          }
          // 其他实例保持不变
          return instance;
        });
      });
    });

    // 组件卸载时清理函数--防止内存泄漏，释放资源
    return () => {
      websocketService.disconnect();
    };
  }, []);

  // 7. JSX 渲染（最后）
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
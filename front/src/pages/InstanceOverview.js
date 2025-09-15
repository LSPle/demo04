import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Tag, Space, Button, message } from 'antd';
import {
  DatabaseOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import apiClient from '../utils/apiClient';
import websocketService from '../services/websocketService';
import { useInstances } from '../contexts/InstanceContext';

const InstanceOverview = () => {
   // 状态管理
  const [loading, setLoading] = useState(false);
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
   
   // 已移除wsConnected状态变量

  // 订阅全局实例上下文
  const { instances, loading: instancesLoading, silentRefreshInstances } = useInstances();

  // 将上下文中的实例映射为当前页面展示结构
  const formattedData = useMemo(() => {
    return (instances || []).map(instance => ({
      key: instance.id,
      name: instance.instanceName,
      // 保留 ip 以兼容，但页面展示改为基于 host/port 渲染
      ip: `${instance.host}:${instance.port}`,
      host: instance.host,
      port: instance.port,
      type: instance.dbType,
      status: instance.status,
      connectionInfo: {
        host: instance.host,
        port: instance.port,
        username: instance.username,
        password: instance.password
      }
    }));
  }, [instances]);
 
 
 
  // 静默拉取实例列表（委托给上下文）
  const fetchInstanceData = async () => {
    await silentRefreshInstances();
  };
 
   // 刷新实例状态
   const refreshInstanceStatus = async () => {
     try {
      setLoading(true);
       message.loading('正在检测实例状态...', 0);
       
       // 调用后端状态检测接口
       const result = await apiClient.checkInstanceStatus();
       
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
 
  // 当数据变化时更新统计
  useEffect(() => {
    updateStatsData(formattedData);
  }, [formattedData]);
 
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
     
     // 已移除连接状态变化监听器
     
      // 已删除未使用的handleInstanceStatusChange和handleStatusSummaryUpdate函数
     
     // 监听所有实例状态更新
     const handleInstancesStatusUpdate = () => {
       // 收到服务端全量更新时，重新拉取当前用户的实例列表
      fetchInstanceData();
     };
     
      // 已禁用状态变更通知监听器
      // websocketService.on('instanceStatusChange', handleInstanceStatusChange);
      // websocketService.on('statusSummaryUpdate', handleStatusSummaryUpdate);
      websocketService.on('instancesStatusUpdate', handleInstancesStatusUpdate);
     
     // 初始获取数据
    fetchInstanceData();
     
     // 已移除定期连接状态检查
     
     // 清理函数
     return () => {
       // 已移除statusInterval清理
        // websocketService.off('instanceStatusChange', handleInstanceStatusChange);
        // websocketService.off('statusSummaryUpdate', handleStatusSummaryUpdate);
        websocketService.off('instancesStatusUpdate', handleInstancesStatusUpdate);
       // 注意：不在这里断开WebSocket连接，因为其他组件可能也在使用
     };
  }, [silentRefreshInstances]);
 
   
 
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
       title: '连接地址',
       key: 'address',
       width: 150,
       render: (_, record) => {
         const host = record.host ?? record.connectionInfo?.host ?? '-';
         const port = record.port ?? record.connectionInfo?.port ?? '-';
         return `${host}:${port}`;
       },
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
           <Button 
             type="primary" 
             icon={<ReloadOutlined />} 
             onClick={refreshInstanceStatus}
            loading={loading || instancesLoading}
           >
             刷新状态
           </Button>
         </div>
       </div>
 
       {/* 数据库实例列表 */}
       <Card className="content-card" style={{ borderRadius: '18px' }}>
         <Table
           columns={columns}
          dataSource={formattedData}
          loading={loading || instancesLoading}
           pagination={{
             current: 1,
             pageSize: 10,
            total: formattedData.length,
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
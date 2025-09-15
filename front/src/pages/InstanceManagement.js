import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Tag, Input, Select, Modal, Form, message, InputNumber } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import apiClient from '../utils/apiClient';
import { useInstances } from '../contexts/InstanceContext';
import websocketService from '../services/websocketService';
import dayjs from 'dayjs';

const { Option } = Select;

const InstanceManagement = () => {
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [instanceData, setInstanceData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form] = Form.useForm();
  const [editingInstance, setEditingInstance] = useState(null);
  // 已移除wsConnected状态变量
  const { onInstanceAdded, onInstanceDeleted, onInstanceUpdated } = useInstances();

  // 从后端获取实例数据
  const fetchInstanceData = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getInstances();
      
      // 转换后端数据格式以匹配前端展示需求
      const formattedData = data.map(instance => ({
        key: instance.id.toString(),
        name: instance.instanceName,
        host: instance.host,
        port: instance.port,
        ip: `${instance.host}:${instance.port}`,
        type: instance.dbType,
        status: instance.status,
        addTime: instance.addTime,
        username: instance.username,
        password: instance.password
      }));
      
      setInstanceData(formattedData);
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
      } else {
        setInstanceData([]);
      }
    } finally {
      setLoading(false);
    }
  };

  // 刷新实例状态（与概览页一致的行为）
  const refreshInstanceStatus = async () => {
    try {
      setLoading(true);
      message.loading('正在检测实例状态...', 0);
      const result = await apiClient.checkInstanceStatus();
      message.destroy();
      message.success(`状态检测完成：总数${result.total}，正常${result.normal}，异常${result.error}`);
      await fetchInstanceData();
    } catch (error) {
      message.destroy();
      console.error('刷新实例状态失败:', error);
      message.error('刷新实例状态失败，请检查后端服务');
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时获取数据
  useEffect(() => {
    fetchInstanceData();
  }, []);

  // WebSocket事件处理
  useEffect(() => {
    // 连接WebSocket
    websocketService.connect();
    
    // 已移除连接状态变化监听器
    
    // 已删除未使用的handleInstanceStatusChange函数
    
    // 监听所有实例状态更新
    const handleInstancesStatusUpdate = (data) => {
      console.log('收到所有实例状态更新:', data);
      if (data.instances) {
        const incoming = data.instances.map(instance => ({
          key: instance.id.toString(),
          name: instance.name,
          host: instance.host,
          port: instance.port,
          ip: `${instance.host}:${instance.port}`,
          type: instance.dbType || 'MySQL',
          status: instance.status,
          // WS 一般不带 addTime；若带则覆盖
          ...(instance.addTime !== undefined ? { addTime: instance.addTime } : {})
        }));
        setInstanceData(prev => {
          const prevMap = new Map(prev.map(item => [item.key, item]));
          return incoming.map(item => {
            const old = prevMap.get(item.key);
            return {
              ...old,
              ...item,
              // WS 不包含账号口令，保留旧值
              username: (old && old.username !== undefined) ? old.username : '',
              password: (old && old.password !== undefined) ? old.password : '',
              // 保留 addTime（若 WS 没有，则沿用旧值）
              addTime: (item.addTime !== undefined)
                ? item.addTime
                : (old && old.addTime !== undefined ? old.addTime : undefined),
            };
          });
        });
      }
    };
    
    // 已禁用状态变更通知监听器
    // websocketService.on('instanceStatusChange', handleInstanceStatusChange);
    websocketService.on('instancesStatusUpdate', handleInstancesStatusUpdate);
    
    // 已移除定期连接状态检查
    
    // 已禁用状态汇总更新监听器
    // const handleStatusSummaryUpdate = () => {
    //     fetchInstanceData();
    // };
    // websocketService.on('statusSummaryUpdate', handleStatusSummaryUpdate);
    
    // 清理函数
    return () => {
      // 已移除statusInterval清理
      // websocketService.off('instanceStatusChange', handleInstanceStatusChange);
      websocketService.off('instancesStatusUpdate', handleInstancesStatusUpdate);
      // websocketService.off('statusSummaryUpdate', handleStatusSummaryUpdate);
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

  const handleEdit = (record) => {
    setEditingInstance(record);
    // 解析IP地址为host和port
    form.setFieldsValue({
      name: record.name,
      type: record.type,
      host: record.host || '',
      port: record.port || 3306,
      username: record.username || '',
      password: record.password || ''
    });
    setIsModalVisible(true);
  };

  const handleDelete = (record) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除实例 "${record.name}" 吗？`,
      okText: '确认',
      cancelText: '取消',
      async onOk() {
        try {
          await apiClient.deleteInstance(record.key);
          message.success('删除成功');
          // 优先通过事件总线携带 id 做增量更新
          websocketService.emit('instanceDeleted', { id: Number(record.key) });
          onInstanceDeleted({ id: Number(record.key) });
          // 回退兜底：仍保留本地表格刷新（仅本页表格，不触发全局刷新）
          fetchInstanceData();
        } catch (error) {
          console.error('删除失败:', error);
          message.error(error.message || '删除失败，请稍后重试');
        }
      }
    });
  };

  const handleAddInstance = () => {
    setEditingInstance(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();

      const host = (values.host || '').trim();
      const portNum = Number(values.port);
      if (!host) {
        message.error('请输入数据库地址');
        return;
      }
      if (!Number.isInteger(portNum) || portNum < 1 || portNum > 65535) {
        message.error('请输入有效端口号（1-65535）');
        return;
      }

      const requestData = {
        name: values.name,
        host: host,
        port: portNum,
        type: values.type,
        username: values.username || '',
        password: values.password || ''
      };

      let response;
      if (editingInstance) {
        // 编辑模式
        response = await apiClient.updateInstance(editingInstance.key, requestData);
      } else {
        // 新增模式
        response = await apiClient.createInstance(requestData);
      }

      const result = response;
      message.success(result.message || '保存成功');
      setIsModalVisible(false);
      form.resetFields();
      const wasEditing = !!editingInstance;
      setEditingInstance(null);
      fetchInstanceData(); // 刷新数据

      // 通知其他组件实例状态已变更
      if (wasEditing) {
        const updatedInst = result.instance || null;
        if (updatedInst) {
          websocketService.emit('instanceUpdated', updatedInst);
          onInstanceUpdated(updatedInst);
        } else {
          onInstanceUpdated();
        }
      } else {
        const newInst = result.instance || null;
        if (newInst) {
          websocketService.emit('instanceAdded', newInst);
          onInstanceAdded(newInst);
        } else {
          onInstanceAdded();
        }
      }

    } catch (error) {
      console.error('保存失败:', error);
      message.error(error.message || '保存失败，请检查输入数据');
    }
  };

  const handleModalCancel = () => {
    setIsModalVisible(false);
    form.resetFields();
  };

  const columns = [
    {
      title: '实例名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <DatabaseOutlined style={{ color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{text}</div>
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>{`${record.host}${record.port ? ':' + record.port : ''}`}</div>
          </div>
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag
    },
    {
      title: '添加时间',
      dataIndex: 'addTime',
      key: 'addTime',
      render: (v) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: setSelectedRowKeys
  };

  return (
    <div>
      {/* 页面标题 */}
      <div className="page-header">
        <div>
          <h1>实例管理</h1>
          <p>添加、删除和配置数据库实例</p>
        </div>
      </div>

      {/* 操作栏 */}
      <Card className="content-card" style={{ marginBottom: 24, borderRadius: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddInstance}
            >
              添加实例
            </Button>
            {selectedRowKeys.length > 0 && (
              <Button danger>
                批量删除 ({selectedRowKeys.length})
              </Button>
            )}
          </Space>
          
          <Space>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={refreshInstanceStatus}
              loading={loading}
            >
              刷新状态
            </Button>
            {/* 已移除搜索框与筛选按钮 */}
          </Space>
        </div>
      </Card>

      {/* 实例列表 */}
      <Card className="content-card" style={{ borderRadius: '18px' }}>
        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={instanceData}
          loading={loading}
          pagination={{
            current: 1,
            pageSize: 10,
            total: instanceData.length,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `显示 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
          }}
        />
      </Card>

      {/* 添加/编辑实例弹窗 */}
      <Modal
        title={editingInstance ? '编辑实例' : '添加实例'}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="name"
            label="实例名称"
            rules={[{ required: true, message: '请输入实例名称' }]}
          >
            <Input placeholder="请输入实例名称" />
          </Form.Item>
          
          <Form.Item
            name="type"
            label="数据库类型"
            rules={[{ required: true, message: '请选择数据库类型' }]}
          >
            <Select placeholder="请选择数据库类型">
              <Option value="MySQL">MySQL</Option>
              <Option value="PostgreSQL">PostgreSQL</Option>
              <Option value="Redis">Redis</Option>
              <Option value="MongoDB">MongoDB</Option>
              <Option value="Oracle">Oracle</Option>
            </Select>
          </Form.Item>

          {/* 新增：拆分地址与端口 */}
          <Form.Item
            name="host"
            label="数据库地址"
            rules={[{ required: true, message: '请输入数据库地址' }]}
          >
            <Input placeholder="例如: mysql2.sqlpub.com 或 192.168.1.100" />
          </Form.Item>

          <Form.Item
            name="port"
            label="端口号"
            rules={[{ required: true, message: '请输入端口号' }]}
          >
            <InputNumber placeholder="3306" min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>

          {/* 删除旧的合并输入字段 ip */}
          {/* 之前的 ip 字段（host:port）已移除 */}
          <Form.Item
            name="username"
            label="用户名"
          >
            <Input placeholder="请输入数据库用户名" />
          </Form.Item>
          
          <Form.Item
            name="password"
            label="密码"
          >
            <Input.Password placeholder="请输入数据库密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default InstanceManagement;
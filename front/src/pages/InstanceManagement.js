import React, { useState, useMemo } from 'react';
import { Card, Table, Button, Space, Input, Select, Modal, Form, message, InputNumber } from 'antd';
import { DatabaseOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getStatusTag } from '../utils/commonUtils';
import apiClient from '../utils/apiClient';
import { useInstances } from '../contexts/InstanceContext';
// 移除未使用的 websocketService 导入
// import websocketService from '../services/websocketService';

const { Option } = Select;

const InstanceManagement = () => {
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  // 删除本地副本，统一从上下文获取
  // const [instanceData, setInstanceData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [editingInstance, setEditingInstance] = useState(null);
  // 已移除wsConnected状态变量
  const { instances, loading: instancesLoading, silentRefreshInstances, onInstanceAdded, onInstanceDeleted, onInstanceUpdated } = useInstances();

  // 统一使用上下文的实例数据
  const formattedData = useMemo(() => {
    return (instances || []).map(instance => ({
      key: String(instance.id),
      name: instance.instanceName,
      host: instance.host,
      port: instance.port,
      ip: `${instance.host}:${instance.port}`,
      type: instance.dbType,
      status: instance.status,
      addTime: instance.addTime,
      username: instance.username,
      password: instance.password,
    }));
  }, [instances]);

  // 删除页面内的拉取函数，改为使用上下文的静默刷新
  // const fetchInstanceData = async () => { ... }

  // 刷新实例状态（与概览页一致的行为）
  const refreshInstanceStatus = async () => {
    try {
      setLoading(true);
      message.loading('正在检测实例状态...', 0);
      const result = await apiClient.checkInstanceStatus();
      message.destroy();
      message.success(`状态检测完成：总数${result.total}，正常${result.normal}，异常${result.error}`);
      await silentRefreshInstances();
    } catch (error) {
      message.destroy();
      console.error('刷新实例状态失败:', error);
      message.error('刷新实例状态失败，请检查后端服务');
    } finally {
      setLoading(false);
    }
  };

  // 移除挂载时本地拉取，依赖全局 InstanceProvider 首次拉取
  // useEffect(() => { fetchInstanceData(); }, []);

  // 移除页面内的 WebSocket 订阅，改由 InstanceContext 统一管理
  // useEffect(() => { websocketService.connect(); ... }, []);

  const handleEdit = (record) => {
    setEditingInstance(record);
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
          // 通过事件总线与上下文增量更新
          onInstanceDeleted({ id: Number(record.key) });
          await silentRefreshInstances();
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
        response = await apiClient.updateInstance(editingInstance.key, requestData);
      } else {
        response = await apiClient.createInstance(requestData);
      }

      const result = response;
      message.success(result.message || '保存成功');
      setIsModalVisible(false);
      form.resetFields();
      const wasEditing = !!editingInstance;
      setEditingInstance(null);
      await silentRefreshInstances();

      if (wasEditing) {
        const updatedInst = result.instance || null;
        if (updatedInst) {
          onInstanceUpdated(updatedInst);
        } else {
          onInstanceUpdated();
        }
      } else {
        const newInst = result.instance || null;
        if (newInst) {
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
              loading={loading || instancesLoading}
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
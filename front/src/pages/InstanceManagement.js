import React, { useState } from 'react';
import { Card, Table, Button, Space, Modal, Form, message, InputNumber, Select, Input } from 'antd';
import { DatabaseOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getStatusTag } from '../utils/commonUtils';
import apiClient from '../utils/apiClient';
import { useInstances } from '../contexts/InstanceContext';

const { Option } = Select;

const InstanceManagement = () => {
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [editingInstance, setEditingInstance] = useState(null);
  
  const { instances, loading: instancesLoading, silentRefreshInstances } = useInstances();

  const tableData = (instances || []).map(instance => ({
    key: String(instance.id),
    name: instance.instanceName,
    host: instance.host,
    port: instance.port,
    type: instance.dbType,
    status: instance.status,
    addTime: instance.addTime,
    username: instance.username,
    password: instance.password,
  }));

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await silentRefreshInstances();
      message.success('实例状态已刷新');
    } catch (error) {
      message.error('刷新失败，请稍后重试');
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
      instanceName: record.name,
      host: record.host,
      port: record.port,
      dbType: record.type,
      username: record.username,
      password: record.password,
    });
    setIsModalVisible(true);
  };

  const handleDelete = async (instanceId) => {
    try {
      await apiClient.deleteInstance(instanceId);
      message.success('删除成功');
      await silentRefreshInstances();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的实例');
      return;
    }
    
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 个实例吗？`,
      onOk: async () => {
        try {
          await Promise.all(selectedRowKeys.map(id => apiClient.deleteInstance(id)));
          message.success('批量删除成功');
          setSelectedRowKeys([]);
          await silentRefreshInstances();
        } catch (error) {
          message.error('批量删除失败');
        }
      },
    });
  };

  const handleAdd = () => {
    setEditingInstance(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      
      if (editingInstance) {
        await apiClient.updateInstance(editingInstance.key, values);
        message.success('更新成功');
      } else {
        await apiClient.addInstance(values);
        message.success('添加成功');
      }
      
      setIsModalVisible(false);
      form.resetFields();
      setEditingInstance(null);
      await silentRefreshInstances();
    } catch (error) {
      if (error.errorFields) {
        message.error('请检查表单输入');
      } else {
        message.error(editingInstance ? '更新失败' : '添加失败');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleModalCancel = () => {
    setIsModalVisible(false);
    form.resetFields();
    setEditingInstance(null);
  };

  const columns = [
    {
      title: '实例名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (text, record) => (
        <Space>
          <DatabaseOutlined style={{ color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{text}</div>
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>{`${record.host}:${record.port}`}</div>
          </div>
        </Space>
      )
    },
    {
      title: '数据库类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type) => type?.toUpperCase() || 'UNKNOWN',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => getStatusTag(status),
    },
    {
      title: '添加时间',
      dataIndex: 'addTime',
      key: 'addTime',
      width: 180,
      render: (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            size="small"
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.key)}
            size="small"
          >
            删除
          </Button>
        </Space>
      ),
    },
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
              onClick={handleAdd}
            >
              添加实例
            </Button>
            {selectedRowKeys.length > 0 && (
              <Button danger onClick={handleBatchDelete}>
                批量删除 ({selectedRowKeys.length})
              </Button>
            )}
          </Space>
          
          <Space>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
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
          dataSource={tableData}
          loading={loading || instancesLoading}
          pagination={{
            current: 1,
            pageSize: 10,
            total: tableData.length,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `显示 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
          }}
        />
      </Card>

      <Modal
        title={editingInstance ? '编辑实例' : '添加实例'}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
        confirmLoading={loading}
        width={600}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 16 }}
          initialValues={{
            dbType: 'mysql',
            port: 3306,
          }}
        >
          <Form.Item
            label="实例名称"
            name="instanceName"
            rules={[
              { required: true, message: '请输入实例名称' },
              { max: 50, message: '实例名称不能超过50个字符' }
            ]}
          >
            <Input placeholder="请输入实例名称" />
          </Form.Item>

          <Form.Item
            label="数据库类型"
            name="dbType"
            rules={[{ required: true, message: '请选择数据库类型' }]}
          >
            <Select placeholder="请选择数据库类型">
              <Option value="mysql">MySQL</Option>
              <Option value="postgresql">PostgreSQL</Option>
              <Option value="oracle">Oracle</Option>
              <Option value="sqlserver">SQL Server</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="主机地址"
            name="host"
            rules={[
              { required: true, message: '请输入主机地址' },
              { max: 255, message: '主机地址不能超过255个字符' }
            ]}
          >
            <Input placeholder="请输入主机地址，如：localhost 或 192.168.1.100" />
          </Form.Item>

          <Form.Item
            label="端口"
            name="port"
            rules={[
              { required: true, message: '请输入端口号' },
              { type: 'number', min: 1, max: 65535, message: '端口号范围：1-65535' }
            ]}
          >
            <InputNumber
              placeholder="请输入端口号"
              style={{ width: '100%' }}
              min={1}
              max={65535}
            />
          </Form.Item>

          <Form.Item
            label="用户名"
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { max: 64, message: '用户名不能超过64个字符' }
            ]}
          >
            <Input placeholder="请输入数据库用户名" />
          </Form.Item>

          <Form.Item
            label="密码"
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { max: 128, message: '密码不能超过128个字符' }
            ]}
          >
            <Input.Password placeholder="请输入数据库密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default InstanceManagement;
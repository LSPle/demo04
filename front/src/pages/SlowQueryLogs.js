import React, { useEffect, useMemo, useState } from 'react';
import { Card, Select, Table, Form, Input, DatePicker, Space, Button, Tag, message, Tooltip, Modal } from 'antd';
import API_BASE_URL, { API_ENDPOINTS } from '../config/api';
import apiClient from '../utils/apiClient';
import dayjs from 'dayjs';
import { useInstances } from '../contexts/InstanceContext';

const { RangePicker } = DatePicker;

const SlowQueryLogs = () => {
  const { getRunningInstanceOptions } = useInstances();
  const instances = getRunningInstanceOptions();
  const [instanceId, setInstanceId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({ items: [], total: 0, overview: {} });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [filters, setFilters] = useState({ keyword: '', db: '', user_host: '', range: [] });
  const [sqlPreview, setSqlPreview] = useState({ visible: false, sql: '', analysis: null });

  // 当实例选择无效时重置
  useEffect(() => {
    if (instanceId && !instances.some(inst => String(inst.id) === String(instanceId))) {
      setInstanceId(null);
      setData({ items: [], total: 0, overview: {} });
      message.warning('所选实例已不可用，选择已重置');
    }
  }, [instanceId, instances]);

  const fetchSlowLogs = async (id, p = page, ps = pageSize, f = filters) => {
    if (!id) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('page', String(p));
      params.set('page_size', String(ps));
      if (f.keyword) params.set('keyword', f.keyword);
      if (f.db) params.set('db', f.db);
      if (f.user_host) params.set('user_host', f.user_host);
      if (Array.isArray(f.range) && f.range.length === 2) {
        params.set('start_time', f.range[0].toISOString());
        params.set('end_time', f.range[1].toISOString());
      }
      const url = `${API_ENDPOINTS.SLOWLOG_LIST(id)}?${params.toString()}`;
      const json = await apiClient.get(url);
      
      console.log('返回的json', json);
      
      if (!json || json.error) {
        // 若后端返回 overview 但报错（比如 FILE 输出），给出提示
        if (json?.overview && String(json?.error || '').includes('TABLE')) {
          message.error('仅支持 log_output=TABLE 的实例，当前实例不满足');
        } else {
          message.error(json?.error || '查询失败');
        }
        setData({ items: [], total: 0, overview: json?.overview || {} });
        return;
      }
      setData(json);
    } catch (e) {
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 实例变化时重置分页并拉取
  useEffect(() => {
    if (instanceId) {
      setPage(1);
      fetchSlowLogs(instanceId, 1, pageSize, filters);
    }
  }, [instanceId]);

  const columns = useMemo(() => [
    {
      title: '查询时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 160,
      sorter: (a, b) => {
        const timeA = a.start_time ? new Date(a.start_time).getTime() : 0;
        const timeB = b.start_time ? new Date(b.start_time).getTime() : 0;
        return timeA - timeB;
      },
      render: (v) => v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '用户和主机',
      dataIndex: 'user_host',
      key: 'user_host',
      width: 180,
      ellipsis: true,
      render: (text) => <Tooltip title={text}>{text}</Tooltip>
    },
    {
      title: '查询语句',
      dataIndex: 'sql_text',
      key: 'sql_text',
      ellipsis: true,
      render: (text) => {
        const SqlTextCell = ({ sql }) => {
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tooltip title={sql}>
                <span style={{ 
                  flex: 1,
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {sql}
                </span>
              </Tooltip>
              {sql && sql.length > 50 && (
                <Button 
                  type="link" 
                  size="small" 
                  style={{ 
                    padding: '0 4px',
                    height: 'auto',
                    fontSize: '12px',
                    flexShrink: 0
                  }} 
                  onClick={() => setSqlPreview({ open: true, sql })}
                >
                  查看全部
                </Button>
              )}
            </div>
          );
        };

        return <SqlTextCell sql={text} />;
      }
    },
    {
      title: '执行时长',
      dataIndex: 'query_time',
      key: 'query_time',
      width: 120,
      sorter: (a, b) => parseFloat(a.query_time || 0) - parseFloat(b.query_time || 0),
      render: (v) => `${v}s`
    },
    {
      title: '返回行数',
      dataIndex: 'rows_sent',
      key: 'rows_sent',
      width: 110,
      sorter: (a, b) => parseInt(a.rows_sent || 0) - parseInt(b.rows_sent || 0)
    },
    {
      title: '锁等待时间',
      dataIndex: 'lock_time',
      key: 'lock_time',
      width: 120,
      sorter: (a, b) => parseFloat(a.lock_time || 0) - parseFloat(b.lock_time || 0),
      render: (v) => `${v}s`
    },
    {
      title: '扫描行数',
      dataIndex: 'rows_examined',
      key: 'rows_examined',
      width: 120,
      sorter: (a, b) => parseInt(a.rows_examined || 0) - parseInt(b.rows_examined || 0)
    }
  ], [setSqlPreview]);

  const onSearch = () => {
    // 手动搜索时立即执行，不使用防抖
    setPage(1);
    fetchSlowLogs(instanceId, 1, pageSize, filters);
  };

  const onReset = () => {
    const nf = { keyword: '', db: '', user_host: '', range: [] };
    setFilters(nf);
    setPage(1);
    // 重置时立即执行搜索
    fetchSlowLogs(instanceId, 1, pageSize, nf);
  };

  return (
    <div style={{ padding: '12px 8px' }}>
      <Card className="content-card" title="慢查询日志" style={{ borderRadius: '18px' }}>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span>目标实例：</span>
            <Select
              style={{ width: 320 }}
              placeholder="请选择实例"
              options={instances}
              value={instanceId}
              onChange={setInstanceId}
              showSearch
              filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
            />
            {data?.overview?.log_output && (
              <Tag color={String(data.overview.log_output).toUpperCase().includes('TABLE') ? 'green' : 'red'}>
                log_output: {data.overview.log_output}
              </Tag>
            )}
          </div>

          {/* 筛选 */}
          <div style={{ background: '#fafafa', padding: 16, borderRadius: 18 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16, marginBottom: 16 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>关键字</label>
                <Input
                  placeholder="SQL包含..."
                  allowClear
                  value={filters.keyword}
                  onChange={e => setFilters(prev => ({ ...prev, keyword: e.target.value }))}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>库名</label>
                <Input
                  placeholder="db 名称"
                  allowClear
                  value={filters.db}
                  onChange={e => setFilters(prev => ({ ...prev, db: e.target.value }))}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>用户/主机</label>
                <Input
                  placeholder="User@Host"
                  allowClear
                  value={filters.user_host}
                  onChange={e => setFilters(prev => ({ ...prev, user_host: e.target.value }))}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>时间范围</label>
                <RangePicker
                  showTime
                  style={{ width: '100%' }}
                  value={filters.range}
                  onChange={(v) => setFilters(prev => ({ ...prev, range: v || [] }))}
                />
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button onClick={onReset}>重置</Button>
                <Button type="primary" onClick={onSearch} disabled={!instanceId}>查询</Button>
              </Space>
            </div>
          </div>

          {/* 表格 */}
          <div style={{ overflowX: 'auto' }}>
            <Table
              rowKey={(r, idx) => `${r.start_time}-${idx}`}
              columns={columns}
              loading={loading}
              dataSource={data.items}
              scroll={{ x: 1200 }}
              pagination={{
                current: page,
                pageSize,
                total: data.total,
                showSizeChanger: true,
                pageSizeOptions: [10, 20, 50, 100],
                showQuickJumper: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                onChange: (p, ps) => {
                  setPage(p);
                  setPageSize(ps);
                  fetchSlowLogs(instanceId, p, ps, filters);
                }
              }}
            />
          </div>
        </Space>
      </Card>

      <Modal open={sqlPreview.open} title="完整SQL" footer={null} onCancel={() => setSqlPreview({ open: false, sql: '' })} width={800} style={{ borderRadius: '18px' }}>
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{sqlPreview.sql}</pre>
      </Modal>
    </div>
  );
};

export default SlowQueryLogs;
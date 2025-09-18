import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined, EyeTwoTone, EyeInvisibleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import API_BASE_URL from '../config/api';
import './Login.css';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const url = isRegister ? '/api/auth/register' : '/api/auth/login';
      const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.message || '操作失败');
      }

      if (isRegister) {
        message.success('注册成功，请登录');
        setIsRegister(false);
      } else {
        // 登录成功，保存用户信息
        localStorage.setItem('userId', data.user.id);
        localStorage.setItem('username', data.user.username);
        message.success('登录成功');
        navigate('/overview');
      }
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-overlay"></div>
      </div>

      <div className="login-content">
        <Card className="login-card fade-in-up">
          <div className="login-header">
            <div className="login-logo">
              <div className="logo-icon" title="MySQL">
                <span className="logo-text">MySQL</span>
              </div>
            </div>
            <h1 className="login-title">数据库优化平台</h1>
            <p className="login-subtitle">Database Optimization Platform</p>
          </div>

          <Form
            name="login"
            size="large"
            onFinish={handleSubmit}
            autoComplete="off"
            className="login-form"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名！' }]}
            >
              <Input
                prefix={<UserOutlined className="input-icon" />}
                placeholder="用户名"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码！' }]}
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="密码"
                className="login-input"
                iconRender={(visible) =>
                  visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
                }
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                className="login-button"
                loading={loading}
                block
              >
                {loading ? (isRegister ? '注册中...' : '登录中...') : (isRegister ? '注册' : '登录')}
              </Button>
            </Form.Item>

            <div style={{ textAlign: 'center' }}>
              <Button type="link" onClick={() => setIsRegister(!isRegister)}>
                {isRegister ? '已有账号？去登录' : '没有账号？去注册'}
              </Button>
            </div>
          </Form>
        </Card>
      </div>
    </div>
  );
};

export default Login;
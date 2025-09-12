import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Checkbox, message, Divider } from 'antd';
import { UserOutlined, LockOutlined, EyeTwoTone, EyeInvisibleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import API_BASE_URL from '../config/api';
import './Login.css';

const Login = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const navigate = useNavigate();

  // 初次加载时尝试填充已记住的用户名
  useEffect(() => {
    const savedUsername = localStorage.getItem('rememberedUsername');
    if (savedUsername) {
      form.setFieldsValue({ username: savedUsername, remember: true });
    }
  }, [form]);

  const handleForgotPassword = (e) => {
    e.preventDefault();
    message.info('请寻找管理员获取密码');
  };

  const handleLogin = async (values) => {
    setLoading(true);
    try {
      if (isRegister) {
        // 注册
        const resp = await fetch(`${API_BASE_URL}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: values.username, password: values.password })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data?.message || '注册失败');
        message.success('注册成功，请继续登录');
        setIsRegister(false);
        return;
      }

      // 登录
      const resp = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: values.username, password: values.password })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.message || '登录失败');

      const user = data?.user;
      if (!user || !user.id) throw new Error('登录响应异常');

      localStorage.setItem('isLoggedIn', 'true');
      localStorage.setItem('username', user.username || values.username);
      localStorage.setItem('userId', String(user.id));
      // 可选保存 token（当前方案不做鉴权使用）
      if (data?.access_token) localStorage.setItem('token', data.access_token);

      // 记住我：仅保存用户名（不保存密码以保障安全）
      if (values.remember) {
        localStorage.setItem('rememberedUsername', values.username);
        localStorage.setItem('rememberMe', 'true');
      } else {
        localStorage.removeItem('rememberedUsername');
        localStorage.removeItem('rememberMe');
      }

      message.success('登录成功！');
      navigate('/overview');
    } catch (error) {
      message.error('登录失败，请重试！');
    } finally {
      setLoading(false);
    }
  };

  const handleLoginFailed = (errorInfo) => {
    message.error('请检查输入信息');
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
            form={form}
            name="login"
            size="large"
            onFinish={handleLogin}
            onFinishFailed={handleLoginFailed}
            autoComplete="off"
            className="login-form"
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名！' }
              ]}
            >
              <Input
                prefix={<UserOutlined className="input-icon" />}
                placeholder="用户名"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码！' }
              ]}
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
              <div className="login-options">
                <Form.Item name="remember" valuePropName="checked" noStyle>
                  <Checkbox className="remember-checkbox">记住我</Checkbox>
                </Form.Item>
                <a className="forgot-password" href="#forgot" onClick={handleForgotPassword}>
                  忘记密码？
                </a>
              </div>
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
              <Button type="link" onClick={() => setIsRegister(v => !v)}>
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
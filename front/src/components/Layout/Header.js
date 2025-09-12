import React from 'react';
import { Layout, Avatar, Dropdown, Space } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';

const { Header: AntHeader } = Layout;

const Header = () => {
  // 读取当前登录用户名
  const username = (localStorage.getItem('username') || '用户').trim();
  const initial = (username[0] || 'U').toUpperCase();

  // 仅保留退出登录功能
  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  const handleMenuClick = ({ key }) => {
    if (key === 'logout') {
      // 清理本地登录态并跳转登录页
      localStorage.removeItem('isLoggedIn');
      localStorage.removeItem('username');
      localStorage.removeItem('userId');
      window.location.href = '/login';
    }
  };

  return (
    <AntHeader
      className="fade-in-up"
      style={{
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(10px)',
        padding: '0 var(--space-xl)',
        borderBottom: '1px solid rgba(240, 240, 240, 0.5)',
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'center',
        boxShadow: 'var(--shadow-md)',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        borderRadius: '0',
      }}
    >
      <Dropdown
        menu={{ items: userMenuItems, onClick: handleMenuClick }}
        placement="bottomRight"
        arrow
      >
        <Space
          style={{
            cursor: 'pointer',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            padding: 'var(--space-xs) var(--space-md)',
            borderRadius: '20px',
            background: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(10px)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.15)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <Avatar
            size={36}
            style={{
              background:
                'linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-2) 100%)',
              fontSize: 14,
              color: '#fff',
              transition: 'all 0.3s ease',
            }}
          >
            {initial}
          </Avatar>
          <span
            style={{
              color: 'var(--color-text)',
              fontSize: 'var(--font-md)',
              fontWeight: 500,
              background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-2) 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            {username}
          </span>
        </Space>
      </Dropdown>
    </AntHeader>
  );
};

export default Header;
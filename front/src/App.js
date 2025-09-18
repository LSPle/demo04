import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Layout } from 'antd';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import InstanceOverview from './pages/InstanceOverview';
import InstanceManagement from './pages/InstanceManagement';
import SQLOptimization from './pages/SQLOptimization';
import SQLConsole from './pages/SQLConsole';
import Login from './pages/Login';
import ArchitectureOptimization from './pages/ArchitectureOptimization';
import SlowQueryLogs from './pages/SlowQueryLogs';
import ConfigOptimization from './pages/ConfigOptimization';
import { InstanceProvider } from './contexts/InstanceContext';

const { Content } = Layout;

// 页面路由配置
const pageRoutes = {
  '/overview': <InstanceOverview />,
  '/management': <InstanceManagement />,
  '/sql-optimization': <SQLOptimization />,
  '/sql-console': <SQLConsole />,
  '/architecture': <ArchitectureOptimization />,
  '/slowlog': <SlowQueryLogs />,
  '/config-optimization': <ConfigOptimization />,
  '/login': <Login />
};

// 主布局组件
const AppLayout = ({ children }) => (
  <Layout style={{ minHeight: '100vh' }}>
    <Sidebar />
    <Layout>
      <Header />
      <Content>
        {children}
      </Content>
    </Layout>
  </Layout>
);

const App = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isAuthenticated = Boolean(localStorage.getItem('userId'));

  // 获取当前页面路径
  const getCurrentPage = () => {
    const pathname = location.pathname;
    // 如果是根路径，返回登录页
    if (pathname === '/') return '/login';
    // 查找匹配的路由
    return Object.keys(pageRoutes).find(route => pathname.startsWith(route)) || '/login';
  };

  const currentPage = getCurrentPage();

  // Keep-Alive: 记录已访问的页面
  const [visitedPages, setVisitedPages] = useState([currentPage]);

  // 当页面变化时，添加到已访问列表
  useEffect(() => {
    if (!visitedPages.includes(currentPage)) {
      setVisitedPages(prev => [...prev, currentPage]);
    }
  }, [currentPage, visitedPages]);

  // 登录检查和重定向
  useEffect(() => {
    // 根路径重定向到登录页
    if (location.pathname === '/') {
      navigate('/login', { replace: true });
      return;
    }

    // 未登录时跳转到登录页
    if (!isAuthenticated && currentPage !== '/login') {
      navigate('/login', { replace: true });
    }
  }, [location.pathname, isAuthenticated, currentPage, navigate]);

  // 渲染所有访问过的页面（Keep-Alive）
  const renderPages = () => {
    return visitedPages.map(pagePath => {
      const pageComponent = pageRoutes[pagePath];
      const isActive = pagePath === currentPage;
      
      return (
        <div 
          key={pagePath}
          style={{ 
            display: isActive ? 'block' : 'none',
            height: '100%'
          }}
        >
          {pageComponent}
        </div>
      );
    });
  };

  // 如果是登录页，直接返回登录组件
  if (currentPage === '/login') {
    return renderPages();
  }

  // 其他页面用AppLayout包装
  return (
    <InstanceProvider>
      <AppLayout>
        {renderPages()}
      </AppLayout>
    </InstanceProvider>
  );
};

export default App;
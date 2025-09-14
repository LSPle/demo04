import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import 'antd/dist/reset.css';
import './index.css';
import { ConfigProvider } from 'antd';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <ConfigProvider theme={{ token: { borderRadius: 18, borderRadiusLG: 18, controlBorderRadius: 18 } }}>
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </React.StrictMode>
);
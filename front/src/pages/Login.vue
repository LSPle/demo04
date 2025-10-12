<template>
  <div class="container">
    <div class="card">
      <!-- 页面标题 -->
      <div class="header">
        <div class="logo">MySQL</div>
        <h1>数据库性能优化平台</h1>
        <p>Database Optimization Platform</p>
      </div>

      <!-- 表单 -->
      <a-form @finish="handleSubmit" :model="form">
        <!-- 用户名输入框 -->
        <a-form-item 
          name="username" 
          :rules="[{ required: true, message: '请输入用户名' }]"
        >
          <a-input 
            v-model:value="form.username" 
            placeholder="用户名"
            size="large"
          >
            <template #prefix>
              <span>👤</span>
            </template>
          </a-input>
        </a-form-item>

        <!-- 密码输入框 -->
        <a-form-item 
          name="password" 
          :rules="[{ required: true, message: '请输入密码' }]"
        >
          <a-input-password 
            v-model:value="form.password" 
            placeholder="密码"
            size="large"
          >
            <template #prefix>
              <span>🔒</span>
            </template>
          </a-input-password>
        </a-form-item>

        <!-- 提交按钮 -->
        <a-form-item>
          <a-button 
            type="primary" 
            html-type="submit" 
            size="large"
            block
          >
            {{ isLogin ? '登录' : '注册' }}
          </a-button>
        </a-form-item>
      </a-form>

      <!-- 切换链接 -->
      <div class="footer">
        <a @click="switchMode">
          {{ isLogin ? '没有账号？ 去注册' : '已有账号？ 去登录' }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import apiClient from '../utils/apiClient';

const router = useRouter();

// 是否为登录模式（true=登录，false=注册）
const isLogin = ref(true);

// 表单数据
const form = reactive({
  username: '',
  password: ''
});

// 切换登录/注册模式
const switchMode = () => {
  isLogin.value = !isLogin.value;
  // 清空表单
  form.username = '';
  form.password = '';
};

// 处理表单提交
const handleSubmit = async (values) => {
  try {
    if (isLogin.value) {
      // 登录
      const result = await apiClient.login(values.username, values.password);
      
      if (result.access_token) {
        // 保存登录信息
        localStorage.setItem('access_token', result.access_token);
        localStorage.setItem('userId', values.username);
        
        message.success('登录成功！');
        router.push('/overview');
      } else {
        message.error('登录失败');
      }
    } else {
      // 注册
      const result = await apiClient.register(values.username, values.password);
      
      if (result.message === 'registered successfully') {
        message.success('注册成功！请登录');
        // 切换到登录模式
        isLogin.value = true;
        // 清空表单
        // form.username = '';
        // form.password = '';
      } else {
        message.error('注册失败');
      }
    }
  } catch (error) {
    console.error('错误:', error);
    if (isLogin.value) {
      message.error('登录失败，请检查用户名和密码');
    } else {
      message.error('注册失败，用户名可能已存在');
    }
  }
};
</script>

<style scoped>
/* 页面容器 */
.container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

/* 登录卡片 */
.card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  text-align: center;
}

/* 头部区域 */
.header {
  margin-bottom: 32px;
}

/* Logo样式 */
.logo {
  background: #6366f1;
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  display: inline-block;
  margin-bottom: 16px;
}

/* 标题样式 */
h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

/* 副标题样式 */
p {
  color: #666;
  font-size: 14px;
  margin: 0 0 24px 0;
}

/* 底部链接 */
.footer {
  margin-top: 24px;
}

.footer a {
  color: #6366f1;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
}

.footer a:hover {
  color: #5856eb;
  text-decoration: underline;
}

/* 表单样式 */
:deep(.ant-input-affix-wrapper) {
  border-radius: 8px !important;
  border: 1px solid #e5e7eb !important;
  background: #f9fafb !important;
  padding: 12px 16px !important;
}

:deep(.ant-input-affix-wrapper:hover) {
  border-color: #6366f1 !important;
  background: white !important;
}

:deep(.ant-input-affix-wrapper-focused) {
  border-color: #6366f1 !important;
  background: white !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1) !important;
}

:deep(.ant-btn-primary) {
  background: #6366f1 !important;
  border: none !important;
  border-radius: 8px !important;
  height: 48px !important;
  font-weight: 600 !important;
  font-size: 16px !important;
}

:deep(.ant-btn-primary:hover) {
  background: #5856eb !important;
}

:deep(.ant-form-item) {
  margin-bottom: 20px !important;
}
</style>
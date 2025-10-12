<template>
  <!-- 登录页面：无布局 -->
  <div v-if="isLoginPage">
    <router-view />
  </div>
  
  <!-- 其他页面：完整布局 -->
  <a-layout v-else style="min-height: 100vh">
    <Sidebar />
    <a-layout>
      <HeaderBar />
      <a-layout-content style="padding: 16px">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import Sidebar from './components/Layout/Sidebar.vue';
import HeaderBar from './components/Layout/Header.vue';

const route = useRoute();

// 判断是否为登录页面
const isLoginPage = computed(() => {
  return route.path === '/login';
});
</script>

<style scoped>
</style>
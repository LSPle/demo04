<template>
  <a-layout-header class="app-header">
    <div class="header-inner">
      <div class="header-right">
        <a-button type="link" @click="goLogin">{{ userLabel }}</a-button>
      </div>
    </div>
  </a-layout-header>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
const router = useRouter();

const userLabel = computed(() => {
  const uid = localStorage.getItem('userId');
  return uid ? `用户：${uid}` : '未登录';
});

function goLogin() {
  router.push('/login');
}
</script>

<style scoped>
.app-header {
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: 0 16px;
  position: relative;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  height: 64px;
}


.header-title {
  font-weight: 600;
  font-size: 16px;
}

.header-right {
  position: absolute;
  top: 8px;
  right: 16px;
  display: flex;
  align-items: center;
}
</style>
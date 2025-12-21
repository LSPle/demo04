<template>
  <a-layout-sider
    class="sidebar-sider"
    :collapsed="collapsed"
    collapsible
    @collapse="onCollapse"
    width="220"
    theme="light"
  >
    <div class="sidebar-header">
      <span v-if="!collapsed" class="sidebar-title">数据库性能优化平台</span>
      <span v-else class="sidebar-title">平台</span>
    </div>
    <a-menu :selectedKeys="selectedKeys" mode="inline" @click="onMenuClick" theme="light" class="sidebar-menu">
      <a-menu-item key="/overview">实例概览</a-menu-item>
      <a-menu-item key="/management">实例管理</a-menu-item>
      <a-menu-item key="/sql-optimization">SQL审核优化</a-menu-item>
      <a-menu-item key="/sql-console">SQL窗口</a-menu-item>
      <a-menu-item key="/architecture">架构优化</a-menu-item>
      <a-menu-item key="/config-optimization">配置优化</a-menu-item>
      <a-menu-item key="/slowlog">慢查询日志</a-menu-item>
    </a-menu>
  </a-layout-sider>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

const collapsed = ref(false);
const selectedKeys = ref([route.path || '/overview']);

watch(() => route.path, (newPath) => {
  selectedKeys.value = [newPath];
});

function onCollapse(val) {
  collapsed.value = val;
}

function onMenuClick({ key }) {
  router.push(key);
}
</script>

<style scoped>
.sidebar-sider {
  background: var(--color-bg);
  border-right: 1px solid var(--color-border);
}

.sidebar-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--color-border);
}

.sidebar-title {
  font-weight: 600;
}


</style>
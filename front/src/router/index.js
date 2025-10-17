import { createRouter, createWebHistory } from 'vue-router';

import InstanceOverview from '../pages/InstanceOverview.vue';
import InstanceManagement from '../pages/InstanceManagement.vue';
import SQLOptimization from '../pages/SQLOptimization.vue';
import SQLConsole from '../pages/SQLConsole.vue';
import ArchitectureOptimization from '../pages/ArchitectureOptimization.vue';
import SlowQueryLogs from '../pages/SlowQueryLogs.vue';
import ConfigOptimization from '../pages/ConfigOptimization.vue';
import Login from '../pages/Login.vue';

const routes = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', component: InstanceOverview, meta: { keepAlive: true } },
  { path: '/management', component: InstanceManagement, meta: { keepAlive: true } },
  { path: '/sql-optimization', component: SQLOptimization, meta: { keepAlive: true } },
  { path: '/sql-console', component: SQLConsole, meta: { keepAlive: true } },
  { path: '/architecture', component: ArchitectureOptimization, meta: { keepAlive: true } },
  { path: '/slowlog', component: SlowQueryLogs, meta: { keepAlive: true } },
  { path: '/config-optimization', component: ConfigOptimization, meta: { keepAlive: true } },
  { path: '/login', component: Login },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
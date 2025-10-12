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
  { path: '/overview', component: InstanceOverview },
  { path: '/management', component: InstanceManagement },
  { path: '/sql-optimization', component: SQLOptimization },
  { path: '/sql-console', component: SQLConsole },
  { path: '/architecture', component: ArchitectureOptimization },
  { path: '/slowlog', component: SlowQueryLogs },
  { path: '/config-optimization', component: ConfigOptimization },
  { path: '/login', component: Login },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
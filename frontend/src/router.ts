import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/gantt', component: () => import('@/views/GanttView.vue') },
  { path: '/gantt/:projectId/task/:taskId', component: () => import('@/views/TaskDetailView.vue') },
  { path: '/tasks', component: () => import('@/views/ProjectListView.vue') },
  { path: '/costs', component: () => import('@/views/CostsView.vue') },
  { path: '/inbox', component: () => import('@/views/InboxView.vue') },
  { path: '/settings', component: () => import('@/views/SettingsView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

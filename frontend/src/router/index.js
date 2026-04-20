import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue')
  },
  {
    path: '/tasks',
    name: 'TaskList',
    component: () => import('@/views/TaskList.vue')
  },
  {
    path: '/tasks/:id',
    name: 'TaskDetail',
    component: () => import('@/views/TaskDetail.vue')
  },
  {
    path: '/config',
    name: 'Config',
    component: () => import('@/views/Config.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

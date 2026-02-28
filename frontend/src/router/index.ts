import { createRouter, createWebHistory } from 'vue-router'

import { authToken } from '../lib/auth'
import AdminFiles from '../views/admin/Files.vue'
import AdminLogin from '../views/admin/Login.vue'
import ShareDownload from '../views/share/ShareDownload.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/admin/files' },
    { path: '/admin/login', component: AdminLogin },
    { path: '/admin/files', component: AdminFiles, meta: { requiresAuth: true } },
    { path: '/s/:shareCode', component: ShareDownload },
    { path: '/:pathMatch(.*)*', redirect: '/admin/login' }
  ]
})

router.beforeEach((to) => {
  if (!to.meta.requiresAuth) return true
  if (authToken.get()) return true
  return { path: '/admin/login', query: { redirect: to.fullPath } }
})

export default router


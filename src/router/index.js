import { createRouter, createWebHistory } from 'vue-router'
import { getStoredUser, getToken } from '../api'
import Login from '../views/Login.vue'
import BookList from '../views/BookList.vue'
import BookDetail from '../views/BookDetail.vue'
import MyLoans from '../views/MyLoans.vue'
import AdminDashboard from '../views/AdminDashboard.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/books' },
    { path: '/login', component: Login, meta: { guestOnly: true } },
    { path: '/books', component: BookList, meta: { requiresAuth: true } },
    { path: '/books/:id', component: BookDetail, meta: { requiresAuth: true } },
    { path: '/loans', component: MyLoans, meta: { requiresAuth: true } },
    { path: '/admin', component: AdminDashboard, meta: { requiresAuth: true, adminOnly: true } },
    { path: '/:pathMatch(.*)*', redirect: '/books' },
  ],
})

router.beforeEach((to) => {
  const authenticated = Boolean(getToken())
  const user = getStoredUser()
  if (to.meta.requiresAuth && !authenticated) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.meta.guestOnly && authenticated) return '/books'
  if (to.meta.adminOnly && user?.role !== 'admin') return '/books'
  return true
})

export default router

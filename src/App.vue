<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NavBar from './components/NavBar.vue'
import { clearSession, getStoredUser } from './api'

const router = useRouter()
const route = useRoute()
const user = ref(getStoredUser())
const isAuthenticated = computed(() => Boolean(user.value))

function refreshSession() {
  user.value = getStoredUser()
}

function logout() {
  clearSession()
  user.value = null
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <NavBar v-if="isAuthenticated" :user="user" @logout="logout" />
    <main :class="['page-container', { 'page-container--public': !isAuthenticated }]">
      <RouterView @session-updated="refreshSession" />
    </main>
    <footer v-if="isAuthenticated && route.path !== '/login'" class="site-footer">
      <span>知行书院 · 让每一次阅读都抵达更远处</span>
      <span>API · {{ 'VITE_API_BASE_URL' }}</span>
    </footer>
  </div>
</template>

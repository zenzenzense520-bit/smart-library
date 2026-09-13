<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['logout'])
const route = useRoute()
const isAdmin = computed(() => route.path.startsWith('/admin'))
</script>

<template>
  <header class="topbar">
    <RouterLink to="/books" class="brand" aria-label="返回书目馆">
      <span class="brand-mark">知</span>
      <span><strong>知行书院</strong><small>智慧图书馆</small></span>
    </RouterLink>
    <nav class="main-nav" aria-label="主导航">
      <RouterLink to="/books" :class="{ active: route.path.startsWith('/books') }">书目馆</RouterLink>
      <RouterLink to="/loans" :class="{ active: route.path === '/loans' }">我的借阅</RouterLink>
      <RouterLink v-if="user.role === 'admin'" to="/admin" :class="{ active: isAdmin }">管理中枢</RouterLink>
    </nav>
    <div class="account-area">
      <div class="avatar">{{ user.name?.slice(0, 1) || '读' }}</div>
      <div class="account-copy"><strong>{{ user.name || user.email }}</strong><small>{{ user.role === 'admin' ? '管理员' : user.role === 'teacher' ? '教职工' : '学生' }}</small></div>
      <button class="icon-button" title="退出登录" @click="emit('logout')">↗</button>
    </div>
  </header>
</template>

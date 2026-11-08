<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { notificationsApi } from '../api'

defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['logout'])
const route = useRoute()
const isAdmin = computed(() => route.path.startsWith('/admin'))

const unreadCount = ref(0)
const notifications = ref([])
const showNotifs = ref(false)
const loadingNotifs = ref(false)

async function fetchUnreadCount() {
  try {
    const data = await notificationsApi.unreadCount()
    unreadCount.value = data.unread_count ?? data.unreadCount ?? 0
  } catch {
    // 忽略未登录或网络波动异常
  }
}

async function toggleNotifs() {
  showNotifs.value = !showNotifs.value
  if (showNotifs.value) {
    loadingNotifs.value = true
    try {
      const data = await notificationsApi.list()
      notifications.value = Array.isArray(data) ? data : data?.results || []
    } catch {
      // 忽略异常
    } finally {
      loadingNotifs.value = false
    }
  }
}

async function markAsRead(notif) {
  if (notif.is_read) return
  try {
    await notificationsApi.markAsRead(notif.id)
    notif.is_read = true
    if (unreadCount.value > 0) unreadCount.value--
  } catch {
    // 忽略
  }
}

async function markAllRead() {
  try {
    await notificationsApi.markAllAsRead()
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  } catch {
    // 忽略
  }
}

function handleClickOutside(e) {
  if (!e.target.closest('.notif-container')) {
    showNotifs.value = false
  }
}

let timer = null
onMounted(() => {
  fetchUnreadCount()
  timer = setInterval(fetchUnreadCount, 30000)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <header class="topbar">
    <RouterLink to="/books" class="brand" aria-label="返回书目馆">
      <span class="brand-mark">知</span>
      <span><strong>知行书院</strong><small>智慧图书馆</small></span>
    </RouterLink>
    <nav class="main-nav" aria-label="主导航">
      <RouterLink to="/books" :class="{ active: route.path.startsWith('/books') }">书目馆</RouterLink>
      <RouterLink to="/loans" :class="{ active: route.path === '/loans' }">借阅与预约</RouterLink>
      <RouterLink v-if="user.role === 'admin'" to="/admin" :class="{ active: isAdmin }">管理中枢</RouterLink>
    </nav>
    <div class="account-area">
      <!-- 消息中心通知铃铛 -->
      <div class="notif-container">
        <button class="notif-bell-btn" title="消息通知" @click.stop="toggleNotifs">
          🔔
          <span v-if="unreadCount > 0" class="notif-badge-pill">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
        </button>
        <div v-if="showNotifs" class="notif-popover" @click.stop>
          <div class="notif-header">
            <strong>消息通知</strong>
            <button v-if="unreadCount > 0" class="text-button" @click="markAllRead">全部标为已读</button>
          </div>
          <div v-if="loadingNotifs" class="notif-empty">正在拉取通知…</div>
          <div v-else-if="!notifications.length" class="notif-empty">暂无任何系统或借还消息</div>
          <div v-else class="notif-list">
            <article
              v-for="item in notifications"
              :key="item.id"
              class="notif-item"
              :class="{ unread: !item.is_read }"
              @click="markAsRead(item)"
            >
              <div class="notif-item-title">
                <span>{{ item.title }}</span>
                <span class="notif-item-time">{{ item.created_at_display || '刚刚' }}</span>
              </div>
              <p class="notif-item-content">{{ item.content }}</p>
            </article>
          </div>
        </div>
      </div>

      <div class="avatar">{{ user.name?.slice(0, 1) || '读' }}</div>
      <div class="account-copy">
        <strong>{{ user.name || user.email }}</strong>
        <small>{{ user.role === 'admin' ? '管理员' : user.role === 'teacher' ? '教职工' : '学生' }}</small>
      </div>
      <button class="icon-button" title="退出登录" @click="emit('logout')">↗</button>
    </div>
  </header>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { booksApi, loansApi, recommendationsApi, reservationsApi } from '../api'

const route = useRoute()
const router = useRouter()
const book = ref(null)
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const myReservation = ref(null)
const relatedBooks = ref([])

const availableCount = computed(() => {
  return book.value ? (book.value.availableCopies ?? book.value.available_copies ?? 0) : 0
})

const isHeldForMe = computed(() => {
  return myReservation.value && myReservation.value.status === 'notified'
})

const isWaitingForMe = computed(() => {
  return myReservation.value && myReservation.value.status === 'waiting'
})

function formatRemainingTime(seconds) {
  if (!seconds || seconds <= 0) return '即将失效'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours} 小时 ${mins} 分钟`
}

async function loadBookData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const bookId = route.params.id
    book.value = await booksApi.get(bookId)

    // 查询当前用户针对该书的预约状态
    try {
      const resData = await reservationsApi.list({ book_id: bookId, status: 'waiting,notified' })
      const items = Array.isArray(resData) ? resData : resData?.results || []
      myReservation.value = items.find(r => ['waiting', 'notified'].includes(r.status)) || null
    } catch {
      // 预约查询失败不阻断页面加载
    }

    // 查询算法推荐的相似书目
    try {
      const related = await recommendationsApi.related(bookId, 4)
      relatedBooks.value = Array.isArray(related) ? related : related?.results || []
    } catch {
      // 忽略
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

async function borrow() {
  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (isHeldForMe.value) {
      await reservationsApi.claim(myReservation.value.id)
      successMessage.value = '🎉 预约核销成功！图书已成功加入您的借阅列表。'
    } else {
      await loansApi.borrow(book.value.id)
      successMessage.value = '借阅成功，书籍已加入你的借阅记录。'
    }
    await loadBookData()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    submitting.value = false
  }
}

async function reserve() {
  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await reservationsApi.create(book.value.id)
    successMessage.value = '预约成功！您已进入排队队列，图书归还后系统将第一时间为您锁定并通知。'
    await loadBookData()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    submitting.value = false
  }
}

async function cancelReservation() {
  if (!myReservation.value) return
  if (!window.confirm('确定放弃此预约排队资格吗？')) return
  submitting.value = true
  errorMessage.value = ''
  try {
    await reservationsApi.cancel(myReservation.value.id)
    successMessage.value = '已成功取消预约。'
    await loadBookData()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    submitting.value = false
  }
}

onMounted(loadBookData)
</script>

<template>
  <div v-if="loading" class="loading">正在打开书目…</div>
  <div v-else-if="errorMessage && !book" class="empty-state">
    <p class="alert">{{ errorMessage }}</p>
    <RouterLink class="button secondary" to="/books">返回书目馆</RouterLink>
  </div>
  <article v-else class="detail-page">
    <RouterLink to="/books" class="back-link">← 返回书目馆</RouterLink>

    <div class="detail-layout">
      <div class="detail-cover book-cover">
        <span>{{ (book.category_name || book.category || 'LIB').slice(0, 3).toUpperCase() }}</span>
        <strong>{{ book.title?.slice(0, 1) }}</strong>
        <small>{{ book.author }}</small>
      </div>

      <div class="detail-copy">
        <p class="eyebrow">{{ book.category_name || book.category || 'Library collection' }}</p>
        <h1 class="page-title">{{ book.title }}</h1>
        <p class="detail-author">{{ book.author }}</p>
        <p class="detail-description">{{ book.description || book.summary || '这本书尚未添加简介。' }}</p>

        <div class="detail-facts">
          <div><span>ISBN</span><strong>{{ book.isbn || '待补充' }}</strong></div>
          <div><span>馆藏总数</span><strong>{{ book.totalCopies ?? book.total_copies ?? '—' }} 本</strong></div>
          <div>
            <span>当前可借</span>
            <strong :class="{ overdue: availableCount < 1 }">{{ availableCount }} 本</strong>
          </div>
        </div>

        <!-- 状态提醒条 -->
        <div v-if="isHeldForMe" class="alert" style="background: #eaf3ec; border-color: #8db69c; color: var(--moss-dark);">
          🎉 <strong>图书已到馆锁定！</strong>系统已为您专属保留（剩余 {{ formatRemainingTime(myReservation.remaining_seconds) }}），请尽快借取。
        </div>

        <div v-else-if="isWaitingForMe" class="alert" style="background: #fbf5ee; border-color: #e5cdb8; color: var(--orange);">
          🕒 <strong>排队预约中：</strong>您当前排在第 {{ myReservation.queue_position }} 位，归还后将按序自动为您保留并发送通知。
        </div>

        <div v-if="errorMessage" class="alert">{{ errorMessage }}</div>
        <div v-if="successMessage" class="success-message">{{ successMessage }}</div>

        <!-- 操作按钮组 -->
        <div style="display: flex; gap: 14px; align-items: center; margin-top: 24px;">
          <!-- 场景 1: 到馆待取专属一键借阅 -->
          <template v-if="isHeldForMe">
            <button class="button" :disabled="submitting" @click="borrow">
              {{ submitting ? '处理中…' : '立即借阅取书 →' }}
            </button>
            <button class="button danger" :disabled="submitting" @click="cancelReservation">
              放弃保留
            </button>
          </template>

          <!-- 场景 2: 正在排队等待中 -->
          <template v-else-if="isWaitingForMe">
            <button class="button secondary" disabled>
              已在排队中（第 {{ myReservation.queue_position }} 位）
            </button>
            <button class="button danger" :disabled="submitting" @click="cancelReservation">
              取消排队
            </button>
          </template>

          <!-- 场景 3: 有空闲副本可直接外借 -->
          <template v-else-if="availableCount > 0">
            <button class="button" :disabled="submitting" @click="borrow">
              {{ submitting ? '提交中…' : '借阅这本书 →' }}
            </button>
          </template>

          <!-- 场景 4: 无库存，支持排队预约 -->
          <template v-else>
            <button class="button" style="background: var(--orange); border-color: var(--orange);" :disabled="submitting" @click="reserve">
              {{ submitting ? '登记中…' : '无现书 · 预约排队登记 →' }}
            </button>
          </template>
        </div>
      </div>
    </div>

    <!-- 详情页相关推荐 -->
    <section v-if="relatedBooks.length" style="margin-top: 72px; padding-top: 36px; border-top: 1px solid var(--line);">
      <div class="section-heading">
        <h2>📚 喜欢这本书的读者还借了</h2>
        <span style="font-size: 12px; color: var(--muted); font-family: 'Segoe UI', sans-serif;">基于共现图谱与同类标签关联推荐</span>
      </div>
      <div class="rec-grid">
        <article v-for="rel in relatedBooks" :key="rel.id" class="rec-card">
          <div>
            <span class="rec-reason">{{ rel.relation_reason || '相似好书' }}</span>
            <h4 class="rec-card-title">{{ rel.title }}</h4>
            <p class="rec-card-author">{{ rel.author }} · {{ rel.category }}</p>
          </div>
          <div class="rec-card-footer">
            <span>{{ (rel.available_copies ?? rel.availableCopies) > 0 ? `${rel.available_copies ?? rel.availableCopies} 本可借` : '需预约排队' }}</span>
            <RouterLink :to="`/books/${rel.id}`" class="text-button" @click="() => setTimeout(loadBookData, 50)">查看书目 →</RouterLink>
          </div>
        </article>
      </div>
    </section>
  </article>
</template>

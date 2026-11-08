<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { loansApi, recommendationsApi, reservationsApi } from '../api'

const activeTab = ref('active') // 'active', 'reservations', 'profile', 'history'
const loans = ref([])
const reservations = ref([])
const userProfile = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const returningId = ref(null)
const processingResId = ref(null)

function normalize(payload) {
  return Array.isArray(payload) ? payload : payload?.items || payload?.results || payload?.loans || []
}

function isOverdue(loan) {
  return loan.status === 'overdue' || (loan.dueDate && new Date(loan.dueDate) < new Date() && !loan.returnedAt && loan.status !== 'returned')
}

function formatTime(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatRemainingTime(seconds) {
  if (!seconds || seconds <= 0) return '即将过期'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours} 小时 ${mins} 分钟`
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [loansData, resData, profileData] = await Promise.all([
      loansApi.mine(),
      reservationsApi.list(),
      recommendationsApi.userProfile(),
    ])
    loans.value = normalize(loansData)
    reservations.value = normalize(resData)
    userProfile.value = profileData
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

async function returnBook(loan) {
  returningId.value = loan.id
  try {
    await loansApi.returnBook(loan.id)
    await loadData()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    returningId.value = null
  }
}

async function claimReservation(res) {
  processingResId.value = res.id
  try {
    await reservationsApi.claim(res.id)
    await loadData()
    activeTab.value = 'active'
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    processingResId.value = null
  }
}

async function cancelReservation(res) {
  if (!window.confirm(`确定取消对《${res.book_title}》的预约吗？`)) return
  processingResId.value = res.id
  try {
    await reservationsApi.cancel(res.id)
    await loadData()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    processingResId.value = null
  }
}

onMounted(loadData)
</script>

<template>
  <section class="loans-page">
    <div class="page-hero">
      <div>
        <p class="eyebrow">Your reading & reservation hub</p>
        <h1 class="page-title">借阅与预约</h1>
        <p class="page-subtitle">管理正在借阅的书籍、跟踪排队到馆动态，并探索专属于您的知行阅读画像。</p>
      </div>
    </div>

    <!-- 标签页切换 -->
    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'active' }" @click="activeTab = 'active'">
        当前在借
        <span class="tab-count">{{ loans.filter(l => !l.returnedAt && l.status !== 'returned').length }}</span>
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'reservations' }" @click="activeTab = 'reservations'">
        预约排队
        <span class="tab-count">{{ reservations.filter(r => ['waiting', 'notified'].includes(r.status)).length }}</span>
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'profile' }" @click="activeTab = 'profile'">
        读者画像 · Reading DNA
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
        借阅历史
      </button>
    </div>

    <div v-if="errorMessage" class="alert">
      {{ errorMessage }} <button class="text-button" @click="loadData">重试</button>
    </div>
    <div v-if="loading" class="loading">正在同步借阅与预约中心数据…</div>

    <!-- Tab 1: 当前借阅 -->
    <div v-else-if="activeTab === 'active'">
      <div v-if="!loans.filter(l => !l.returnedAt && l.status !== 'returned').length" class="empty-state">
        您当前没有借阅中的图书，去书目馆挑选一本吧。
      </div>
      <div v-else class="loan-list">
        <article
          v-for="loan in loans.filter(l => !l.returnedAt && l.status !== 'returned')"
          :key="loan.id"
          class="loan-row"
        >
          <div class="loan-index">{{ String(loan.book_title || loan.book?.title || '书').slice(0, 1) }}</div>
          <div class="loan-main">
            <h2>{{ loan.book_title || loan.book?.title || '未命名书目' }}</h2>
            <p>{{ loan.book_author || loan.book?.author || '未知作者' }}</p>
          </div>
          <div class="loan-date">
            <span>应还日期</span>
            <strong :class="{ overdue: isOverdue(loan) }">{{ formatTime(loan.due_at || loan.dueDate) }}</strong>
          </div>
          <div class="loan-status" :class="{ overdue: isOverdue(loan) }">
            {{ isOverdue(loan) ? '⚠️ 已逾期' : '借阅中' }}
          </div>
          <button
            class="button secondary"
            :disabled="returningId === loan.id"
            @click="returnBook(loan)"
          >
            {{ returningId === loan.id ? '处理中…' : '归还' }}
          </button>
        </article>
      </div>
    </div>

    <!-- Tab 2: 预约排队与到馆提醒 -->
    <div v-else-if="activeTab === 'reservations'">
      <div v-if="!reservations.length" class="empty-state">
        您暂无任何图书预约。当心仪的书目被借空时，可在详情页一键加入排队预约。
      </div>
      <div v-else class="res-list">
        <article
          v-for="res in reservations"
          :key="res.id"
          class="res-card"
          :class="{ held: res.status === 'notified', waiting: res.status === 'waiting' }"
        >
          <div class="res-card-avatar">{{ String(res.book_title || '预').slice(0, 1) }}</div>
          <div class="res-card-main">
            <h3>{{ res.book_title }}</h3>
            <p>{{ res.book_author }} · {{ res.book_category }} · 登记于 {{ formatTime(res.reserved_at) }}</p>
            <div>
              <span v-if="res.status === 'notified'" class="res-status-tag tag-held">
                🎉 图书已到馆保留中
              </span>
              <span v-else-if="res.status === 'waiting'" class="res-status-tag tag-waiting">
                🕒 排队等待中（前方还有 {{ Math.max(0, (res.queue_position || 1) - 1) }} 人）
              </span>
              <span v-else-if="res.status === 'fulfilled'" class="res-status-tag tag-done">
                ✓ 已完成借阅
              </span>
              <span v-else-if="res.status === 'expired'" class="res-status-tag tag-done">
                ✕ 超时未取已失效
              </span>
              <span v-else class="res-status-tag tag-done">
                已取消
              </span>

              <span v-if="res.status === 'notified'" class="res-countdown">
                ⏳ 保留剩余：{{ formatRemainingTime(res.remaining_seconds) }}
              </span>
            </div>
          </div>
          <div class="res-actions">
            <!-- 到馆待取一键核销借阅 -->
            <button
              v-if="res.status === 'notified'"
              class="button"
              :disabled="processingResId === res.id"
              @click="claimReservation(res)"
            >
              {{ processingResId === res.id ? '借取中…' : '立即借阅取书 →' }}
            </button>
            <!-- 排队中或到馆中支持主动取消 -->
            <button
              v-if="['waiting', 'notified'].includes(res.status)"
              class="button secondary"
              :disabled="processingResId === res.id"
              @click="cancelReservation(res)"
            >
              取消预约
            </button>
          </div>
        </article>
      </div>
    </div>

    <!-- Tab 3: 读者画像 (Reading DNA) -->
    <div v-else-if="activeTab === 'profile'">
      <div v-if="!userProfile" class="empty-state">正在计算读者画像…</div>
      <div v-else>
        <div class="profile-box">
          <!-- DNA 核心卡片 -->
          <div class="dna-banner">
            <div>
              <span class="dna-badge">Reader DNA Portrait</span>
              <h2>{{ userProfile.reading_dna_label }}</h2>
              <p>{{ userProfile.reading_dna_desc }}</p>
            </div>
            <div class="dna-metrics">
              <div class="dna-metric-item">
                <span>累计借阅书目</span>
                <strong>{{ userProfile.total_loans }} 本</strong>
              </div>
              <div class="dna-metric-item">
                <span>守信准时履约率</span>
                <strong style="color: #9fe2bf;">{{ userProfile.on_time_return_rate }}%</strong>
              </div>
            </div>
          </div>

          <!-- 分类偏好分布 -->
          <div class="cat-breakdown">
            <h4>📊 偏好领域分布</h4>
            <div v-if="!userProfile.top_categories.length" style="color: var(--muted); font-size: 12px;">
              暂无借阅记录，多借阅几本好书即可点亮分类雷达。
            </div>
            <div v-for="cat in userProfile.top_categories" :key="cat.name" class="cat-row">
              <div class="cat-row-label">
                <span>{{ cat.name }}</span>
                <strong>{{ cat.count }} 本 ({{ cat.percentage }}%)</strong>
              </div>
              <div class="cat-track">
                <div class="cat-bar" :style="{ width: `${cat.percentage}%` }"></div>
              </div>
            </div>

            <!-- 常读作者 -->
            <div v-if="userProfile.top_authors.length" style="margin-top: 10px; border-top: 1px solid var(--line); padding-top: 14px;">
              <h4 style="margin-bottom: 8px;">🖋️ 常读作者</h4>
              <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                <span
                  v-for="a in userProfile.top_authors"
                  :key="a.name"
                  class="rec-reason"
                  style="font-size: 11px;"
                >
                  {{ a.name }} ({{ a.count }}本)
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 4: 借阅历史 -->
    <div v-else-if="activeTab === 'history'">
      <div v-if="!loans.filter(l => l.returnedAt || l.status === 'returned').length" class="empty-state">
        暂无已归还的历史记录。
      </div>
      <div v-else class="loan-list">
        <article
          v-for="loan in loans.filter(l => l.returnedAt || l.status === 'returned')"
          :key="loan.id"
          class="loan-row"
        >
          <div class="loan-index" style="background: #a3aba5;">{{ String(loan.book_title || loan.book?.title || '书').slice(0, 1) }}</div>
          <div class="loan-main">
            <h2>{{ loan.book_title || loan.book?.title || '未命名书目' }}</h2>
            <p>{{ loan.book_author || loan.book?.author || '未知作者' }}</p>
          </div>
          <div class="loan-date">
            <span>归还日期</span>
            <strong>{{ formatTime(loan.returned_at || loan.returnedAt) }}</strong>
          </div>
          <div class="loan-status">
            {{ Number(loan.fine_amount) > 0 ? `逾期罚款 ¥${loan.fine_amount}` : '正常还回' }}
          </div>
          <span style="font-family: 'Segoe UI', sans-serif; font-size: 11px; color: var(--muted);">已完结</span>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { adminApi } from '../api'

const stats = ref(null)
const loading = ref(true)
const errorMessage = ref('')

async function loadStats() {
  try {
    stats.value = await adminApi.stats()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <section class="admin-page">
    <div class="page-hero">
      <div>
        <p class="eyebrow">Operations desk</p>
        <h1 class="page-title">管理中枢</h1>
        <p class="page-subtitle">掌握书目流动与校园阅读热度，调度预约排队与库存顺延，让每一本书都被高效流转。</p>
      </div>
      <RouterLink to="/books" class="button secondary">进入书目馆 →</RouterLink>
    </div>

    <div v-if="errorMessage" class="alert">
      {{ errorMessage }} <button class="text-button" @click="loadStats">重试</button>
    </div>
    <div v-if="loading" class="loading">正在汇总馆务数据…</div>
    <template v-else-if="stats">
      <div class="stat-grid" style="grid-template-columns: repeat(6, 1fr);">
        <div class="stat-card">
          <span>馆藏总量</span>
          <strong>{{ stats.totalBooks ?? stats.totalCopies ?? '—' }}</strong>
          <small>本书目</small>
        </div>
        <div class="stat-card accent">
          <span>当前可借</span>
          <strong>{{ stats.availableBooks ?? stats.availableCopies ?? '—' }}</strong>
          <small>册流通中</small>
        </div>
        <div class="stat-card">
          <span>外借中</span>
          <strong>{{ stats.activeLoans ?? stats.borrowedCount ?? '—' }}</strong>
          <small>笔记录</small>
        </div>
        <div class="stat-card warning">
          <span>逾期借阅</span>
          <strong>{{ stats.overdueLoans ?? stats.overdueCount ?? '—' }}</strong>
          <small>需关注催还</small>
        </div>
        <div class="stat-card" style="background: #eef3ed;">
          <span>预约排队中</span>
          <strong style="color: var(--moss-dark);">{{ stats.waiting_reservations ?? stats.waitingReservations ?? 0 }}</strong>
          <small>位读者排队</small>
        </div>
        <div class="stat-card" style="background: #faf3e8;">
          <span>到馆保留中</span>
          <strong style="color: var(--orange);">{{ stats.notified_reservations ?? stats.notifiedReservations ?? 0 }}</strong>
          <small>册待取锁定</small>
        </div>
      </div>

      <!-- 热门借阅榜单 -->
      <section v-if="stats.popular_books && stats.popular_books.length" style="margin-top: 32px; padding: 24px; background: var(--paper); border: 1px solid var(--line);">
        <div class="section-heading" style="margin-bottom: 16px;">
          <h2>🔥 全馆借阅排行榜 TOP 10</h2>
          <span style="font-size: 12px; color: var(--muted); font-family: 'Segoe UI', sans-serif;">算法统计借阅热度与流通频次</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
          <div
            v-for="(book, index) in stats.popular_books"
            :key="book.id"
            style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--cream); font-family: 'Segoe UI', sans-serif; font-size: 13px;"
          >
            <span><strong>#{{ index + 1 }}</strong> 《{{ book.title }}》</span>
            <span style="color: var(--orange); font-weight: 600;">借阅 {{ book.borrow_count }} 次</span>
          </div>
        </div>
      </section>

      <section class="admin-note">
        <div>
          <p class="eyebrow">Smart Library Intelligence</p>
          <h2>让智能算法与状态机赋能现代馆务</h2>
          <p>排队预约自动顺延（FIFO）、到馆专属库存锁定（48小时倒计时）、读者偏好画像协同过滤推荐全面运作中。</p>
        </div>
        <span class="note-mark">↗</span>
      </section>
    </template>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { adminApi } from '../api'

const stats = ref(null); const loading = ref(true); const errorMessage = ref('')
async function loadStats() { try { stats.value = await adminApi.stats() } catch (error) { errorMessage.value = error.message } finally { loading.value = false } }
onMounted(loadStats)
</script>

<template>
  <section class="admin-page"><div class="page-hero"><div><p class="eyebrow">Operations desk</p><h1 class="page-title">管理中枢</h1><p class="page-subtitle">掌握书目流动与校园阅读热度，让每一本书都被更好地使用。</p></div><RouterLink to="/books" class="button secondary">进入书目馆 →</RouterLink></div><div v-if="errorMessage" class="alert">{{ errorMessage }} <button class="text-button" @click="loadStats">重试</button></div><div v-if="loading" class="loading">正在汇总馆务数据…</div><template v-else-if="stats"><div class="stat-grid"><div class="stat-card"><span>馆藏总量</span><strong>{{ stats.totalBooks ?? stats.totalCopies ?? '—' }}</strong><small>本书目</small></div><div class="stat-card accent"><span>当前可借</span><strong>{{ stats.availableBooks ?? stats.availableCopies ?? '—' }}</strong><small>可流通</small></div><div class="stat-card"><span>借阅中</span><strong>{{ stats.activeLoans ?? stats.borrowedCount ?? '—' }}</strong><small>笔记录</small></div><div class="stat-card warning"><span>逾期未还</span><strong>{{ stats.overdueLoans ?? stats.overdueCount ?? '—' }}</strong><small>需要关注</small></div></div><section class="admin-note"><div><p class="eyebrow">Today’s focus</p><h2>让数据服务于阅读</h2><p>从借阅趋势、热门分类和逾期记录中发现书架需要的下一步。</p></div><span class="note-mark">↗</span></section></template></section>
</template>

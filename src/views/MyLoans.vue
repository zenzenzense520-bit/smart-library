<script setup>
import { onMounted, ref } from 'vue'
import { loansApi } from '../api'

const loans = ref([]); const loading = ref(true); const errorMessage = ref(''); const returningId = ref(null)
function normalize(payload) { return Array.isArray(payload) ? payload : payload?.items || payload?.loans || [] }
function isOverdue(loan) { return loan.status === 'overdue' || (loan.dueDate && new Date(loan.dueDate) < new Date() && !loan.returnedAt) }
async function loadLoans() { try { loans.value = normalize(await loansApi.mine()) } catch (error) { errorMessage.value = error.message } finally { loading.value = false } }
async function returnBook(loan) { returningId.value = loan.id; try { await loansApi.returnBook(loan.id); await loadLoans() } catch (error) { errorMessage.value = error.message } finally { returningId.value = null } }
onMounted(loadLoans)
</script>

<template>
  <section class="loans-page"><div class="page-hero"><div><p class="eyebrow">Your reading trail</p><h1 class="page-title">我的借阅</h1><p class="page-subtitle">把正在阅读的书放在手边，也别忘了让它们按时回到书架。</p></div></div><div v-if="errorMessage" class="alert">{{ errorMessage }} <button class="text-button" @click="loadLoans">重试</button></div><div v-if="loading" class="loading">正在读取借阅记录…</div><div v-else-if="!loans.length" class="empty-state">你还没有借阅记录，去书目馆发现一本书吧。</div><div v-else class="loan-list"><article v-for="loan in loans" :key="loan.id" class="loan-row"><div class="loan-index">{{ String(loan.book?.title || '书').slice(0, 1) }}</div><div class="loan-main"><h2>{{ loan.book?.title || loan.title || '未命名书目' }}</h2><p>{{ loan.book?.author || loan.author || '未知作者' }}</p></div><div class="loan-date"><span>应还日期</span><strong :class="{ overdue: isOverdue(loan) }">{{ loan.dueDate ? new Date(loan.dueDate).toLocaleDateString('zh-CN') : '—' }}</strong></div><div class="loan-status" :class="{ overdue: isOverdue(loan) }">{{ loan.returnedAt || loan.status === 'returned' ? '已归还' : isOverdue(loan) ? '已逾期' : '借阅中' }}</div><button v-if="!loan.returnedAt && loan.status !== 'returned'" class="button secondary" :disabled="returningId === loan.id" @click="returnBook(loan)">{{ returningId === loan.id ? '处理中' : '归还' }}</button></article></div></section>
</template>

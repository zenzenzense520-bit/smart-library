<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { booksApi, loansApi } from '../api'

const route = useRoute(); const router = useRouter()
const book = ref(null); const loading = ref(true); const submitting = ref(false); const errorMessage = ref(''); const successMessage = ref('')
async function loadBook() { try { book.value = await booksApi.get(route.params.id) } catch (error) { errorMessage.value = error.message } finally { loading.value = false } }
async function borrow() { submitting.value = true; errorMessage.value = ''; successMessage.value = ''; try { await loansApi.borrow(book.value.id); successMessage.value = '借阅成功，书籍已加入你的借阅记录。'; await loadBook() } catch (error) { errorMessage.value = error.message } finally { submitting.value = false } }
onMounted(loadBook)
</script>

<template>
  <div v-if="loading" class="loading">正在打开书目…</div>
  <div v-else-if="errorMessage && !book" class="empty-state"><p class="alert">{{ errorMessage }}</p><RouterLink class="button secondary" to="/books">返回书目馆</RouterLink></div>
  <article v-else class="detail-page">
    <RouterLink to="/books" class="back-link">← 返回书目馆</RouterLink>
    <div class="detail-layout"><div class="detail-cover book-cover"><span>{{ (book.category || 'LIB').slice(0, 3).toUpperCase() }}</span><strong>{{ book.title?.slice(0, 1) }}</strong><small>{{ book.author }}</small></div><div class="detail-copy"><p class="eyebrow">{{ book.category || 'Library collection' }}</p><h1 class="page-title">{{ book.title }}</h1><p class="detail-author">{{ book.author }}</p><p class="detail-description">{{ book.description || '这本书尚未添加简介。' }}</p><div class="detail-facts"><div><span>ISBN</span><strong>{{ book.isbn || '待补充' }}</strong></div><div><span>馆藏</span><strong>{{ book.totalCopies ?? '—' }} 本</strong></div><div><span>可借</span><strong>{{ book.availableCopies ?? book.available ?? 0 }} 本</strong></div></div><div v-if="errorMessage" class="alert">{{ errorMessage }}</div><div v-if="successMessage" class="success-message">{{ successMessage }}</div><button class="button" :disabled="submitting || !(book.availableCopies ?? book.available)" @click="borrow">{{ submitting ? '提交中…' : '借阅这本书 →' }}</button></div></div>
  </article>
</template>

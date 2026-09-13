<script setup>
import { onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { booksApi, getStoredUser } from '../api'

const books = ref([])
const isAdmin = getStoredUser()?.role === 'admin'
const loading = ref(true)
const errorMessage = ref('')
const showForm = ref(false)
const editingId = ref(null)
const filters = reactive({ search: '', category: '', author: '' })
const form = reactive({ title: '', author: '', category: '', isbn: '', totalCopies: 1, description: '' })

function normalizeBooks(payload) { return Array.isArray(payload) ? payload : payload?.items || payload?.books || [] }
async function loadBooks() {
  loading.value = true
  errorMessage.value = ''
  try { books.value = normalizeBooks(await booksApi.list(filters)) } catch (error) { errorMessage.value = error.message } finally { loading.value = false }
}
function resetForm() { Object.assign(form, { title: '', author: '', category: '', isbn: '', totalCopies: 1, description: '' }); editingId.value = null }
function openCreate() { resetForm(); showForm.value = true }
function openEdit(book) { Object.assign(form, book); editingId.value = book.id; showForm.value = true }
async function saveBook() {
  try { editingId.value ? await booksApi.update(editingId.value, form) : await booksApi.create(form); showForm.value = false; await loadBooks() } catch (error) { errorMessage.value = error.message }
}
async function removeBook(book) {
  if (!window.confirm(`确定删除《${book.title}》吗？`)) return
  try { await booksApi.remove(book.id); await loadBooks() } catch (error) { errorMessage.value = error.message }
}
function available(book) { return book.availableCopies ?? book.available ?? 0 }
onMounted(loadBooks)
</script>

<template>
  <div class="library-page">
    <section class="page-hero">
      <div><p class="eyebrow">Explore the collection</p><h1 class="page-title">书目馆</h1><p class="page-subtitle">从经典理论到当代思潮，浏览校园知识的横截面。你的下一次灵感，可能正在这里等待。</p></div>
      <button v-if="isAdmin" class="button" @click="openCreate">添加书目 +</button>
    </section>
    <section class="filter-bar">
      <label class="search-field"><span>⌕</span><input v-model="filters.search" placeholder="搜索书名、关键词…" @keyup.enter="loadBooks" /></label>
      <input v-model="filters.author" class="filter-input" placeholder="作者" @keyup.enter="loadBooks" />
      <input v-model="filters.category" class="filter-input" placeholder="分类" @keyup.enter="loadBooks" />
      <button class="button secondary" @click="loadBooks">筛选</button>
    </section>
    <div v-if="errorMessage" class="alert">{{ errorMessage }} <button class="text-button" @click="loadBooks">重试</button></div>
    <div v-if="loading" class="loading">正在整理书架…</div>
    <div v-else-if="!books.length" class="empty-state">没有找到匹配的书目。试试换个关键词。</div>
    <section v-else class="book-grid">
      <article v-for="book in books" :key="book.id" class="book-card">
        <div class="book-cover"><span>{{ (book.category || 'LIB').slice(0, 3).toUpperCase() }}</span><strong>{{ book.title?.slice(0, 1) }}</strong><small>{{ book.author }}</small></div>
        <div class="book-info"><p class="book-category">{{ book.category || '未分类' }}</p><h2>{{ book.title }}</h2><p class="book-author">{{ book.author }}</p><div class="book-meta"><span :class="{ 'is-low': available(book) < 2 }">{{ available(book) ? `${available(book)} 本可借` : '暂不可借' }}</span><RouterLink :to="`/books/${book.id}`">查看详情 →</RouterLink></div><div v-if="isAdmin" class="admin-actions"><button class="text-button" @click="openEdit(book)">编辑</button><button class="text-button danger-text" @click="removeBook(book)">删除</button></div></div>
      </article>
    </section>
    <div v-if="showForm" class="modal-backdrop" @click.self="showForm = false"><form class="modal-panel" @submit.prevent="saveBook"><div class="section-heading"><h2>{{ editingId ? '编辑书目' : '新增书目' }}</h2><button type="button" class="close-button" @click="showForm = false">×</button></div><div class="form-grid"><label><span class="field-label">书名</span><input v-model="form.title" class="field-input" required /></label><label><span class="field-label">作者</span><input v-model="form.author" class="field-input" required /></label><label><span class="field-label">分类</span><input v-model="form.category" class="field-input" /></label><label><span class="field-label">馆藏数量</span><input v-model.number="form.totalCopies" class="field-input" type="number" min="1" /></label><label class="form-field full"><span class="field-label">简介</span><textarea v-model="form.description" class="field-textarea" /></label></div><button class="button" type="submit">保存书目</button></form></div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi, setSession } from '../api'

const router = useRouter()
const route = useRoute()
const isRegister = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const form = reactive({ name: '', email: '', password: '', role: 'student' })
const title = computed(() => isRegister.value ? '加入知行书院' : '欢迎回来')

async function submit() {
  errorMessage.value = ''
  if (!form.email || !form.password || (isRegister.value && !form.name)) {
    errorMessage.value = '请完整填写必填信息。'
    return
  }
  loading.value = true
  try {
    const registerData = { ...form, role: form.role === 'teacher' ? 'staff' : form.role }
    const payload = isRegister.value ? await authApi.register(registerData) : await authApi.login({ email: form.email, password: form.password })
    if (!payload.token) {
      const loginPayload = await authApi.login({ email: form.email, password: form.password })
      setSession(loginPayload)
    } else {
      setSession(payload)
    }
    router.push(route.query.redirect || '/books')
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <section class="auth-intro">
      <p class="eyebrow">Zhi Xing Library · 2026</p>
      <h1>让知识<br /><em>被看见。</em></h1>
      <p>一座面向大学校园的数字书院。发现下一本值得阅读的书，留下你的借阅轨迹。</p>
      <div class="intro-note"><span>01</span><span>藏书 · 借阅 · 生长</span></div>
    </section>
    <section class="auth-panel">
      <p class="eyebrow">{{ isRegister ? 'New member' : 'Member access' }}</p>
      <h2>{{ title }}</h2>
      <p class="auth-hint">{{ isRegister ? '创建账户，开启你的校园阅读档案。' : '使用校园账户登录智慧图书馆。' }}</p>
      <div v-if="errorMessage" class="alert">{{ errorMessage }}</div>
      <form class="auth-form" @submit.prevent="submit">
        <label v-if="isRegister"><span class="field-label">姓名</span><input v-model="form.name" class="field-input" placeholder="你的姓名" autocomplete="name" /></label>
        <label><span class="field-label">校园邮箱</span><input v-model="form.email" class="field-input" type="email" placeholder="name@university.edu.cn" autocomplete="email" /></label>
        <label><span class="field-label">密码</span><input v-model="form.password" class="field-input" type="password" placeholder="至少 6 位字符" autocomplete="current-password" /></label>
        <label v-if="isRegister"><span class="field-label">身份</span><select v-model="form.role" class="field-select"><option value="student">学生</option><option value="staff">教职工</option><option value="admin">管理员</option></select></label>
        <button class="button auth-submit" :disabled="loading">{{ loading ? '正在处理…' : (isRegister ? '创建账户' : '进入书院') }} <span>→</span></button>
      </form>
      <button class="auth-switch" @click="isRegister = !isRegister; errorMessage = ''">{{ isRegister ? '已有账户？返回登录' : '首次使用？创建账户' }}</button>
    </section>
  </div>
</template>

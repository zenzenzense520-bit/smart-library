const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')
const TOKEN_KEY = 'smart-library-token'
const USER_KEY = 'smart-library-user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getStoredUser() {
  const rawUser = localStorage.getItem(USER_KEY)
  if (!rawUser) return null

  try {
    return JSON.parse(rawUser)
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function setSession(session) {
  localStorage.setItem(TOKEN_KEY, session.token)
  localStorage.setItem(USER_KEY, JSON.stringify(session.user))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  } catch {
    throw new Error('无法连接服务器，请检查后端是否已启动。')
  }

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    if (response.status === 401) clearSession()
    const message = getErrorMessage(payload, response.status)
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return payload
}

function getErrorMessage(payload, responseStatus) {
  if (typeof payload === 'string' && payload.trim()) return payload
  if (payload?.message) return payload.message
  if (payload && typeof payload === 'object') {
    const details = Object.entries(payload)
      .flatMap(([field, messages]) => (Array.isArray(messages) ? messages : [messages]).map((message) => `${field}: ${message}`))
    if (details.length) return details.join('；')
  }
  return `请求失败（${responseStatus}）`
}

function jsonBody(data) {
  return JSON.stringify(data)
}

export const authApi = {
  login: (data) => request('/auth/login', { method: 'POST', body: jsonBody(data) }),
  register: (data) => request('/auth/register', { method: 'POST', body: jsonBody(data) }),
}

export const booksApi = {
  list: (params = {}) => {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') query.set(key, value)
    })
    return request(`/books${query.toString() ? `?${query}` : ''}`)
  },
  get: (id) => request(`/books/${id}`),
  create: (data) => request('/books', { method: 'POST', body: jsonBody(data) }),
  update: (id, data) => request(`/books/${id}`, { method: 'PUT', body: jsonBody(data) }),
  remove: (id) => request(`/books/${id}`, { method: 'DELETE' }),
}

export const loansApi = {
  mine: () => request('/loans/my'),
  borrow: (bookId) => request('/loans', { method: 'POST', body: jsonBody({ book_id: bookId }) }),
  returnBook: (id) => request(`/loans/${id}/return`, { method: 'PATCH' }),
}

export const adminApi = {
  stats: () => request('/admin/stats'),
}

export const apiConfig = { baseUrl: API_BASE_URL }

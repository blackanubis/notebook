import axios from 'axios'
import { showToast } from 'vant'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 90000,
})

api.interceptors.response.use(
  r => r,
  err => {
    const msg = err?.response?.data?.detail || err.message || '请求失败'
    showToast({ message: msg, type: 'fail', duration: 3000 })
    return Promise.reject(err)
  }
)

export default api

// ============ 封装业务 API ============

export const childrenApi = {
  list: () => api.get('/children'),
  create: (data) => api.post('/children', data),
  update: (id, data) => api.put(`/children/${id}`, data),
  remove: (id) => api.delete(`/children/${id}`),
}

export const questionApi = {
  list: (params) => api.get('/questions', { params }),
  get: (id) => api.get(`/questions/${id}`),
  create: (data) => api.post('/questions', data),
  update: (id, data) => api.put(`/questions/${id}`, data),
  remove: (id) => api.delete(`/questions/${id}`),
}

export const ocrApi = {
  recognize: (data) => api.post('/ocr/recognize', data),
}

export const aiApi = {
  analyzeError: (data) => api.post('/ai/analyze-error', data),
  similarQuestions: (data) => api.post('/ai/similar-questions', data),
  judge: (data) => api.post('/practice/judge', data),
}

export const uploadApi = {
  image: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/upload/image', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export const exportApi = {
  pdf: (data) => api.post('/export/pdf', data),
}

export const reportApi = {
  generate: (child_id, report_type = 'weekly') => api.post(`/reports/generate?child_id=${child_id}&report_type=${report_type}`),
  list: (child_id) => api.get('/reports', { params: { child_id } }),
  get: (id) => api.get(`/reports/${id}`),
}

export const settingsApi = {
  getAI: () => api.get('/settings/ai'),
  updateAI: (data) => api.put('/settings/ai', data),
  status: () => api.get('/settings/ai/status'),
}

export const statsApi = {
  summary: (child_id) => api.get('/stats/summary', { params: { child_id } }),
}

export const practiceApi = {
  save: (formData) => api.post('/practice/save', formData),
}
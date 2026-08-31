<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">错题本</div>
      <van-icon name="filter" size="20" @click="showFilter = true" />
    </div>

    <!-- 筛选 -->
    <div class="card" style="margin:10px 12px;padding:10px">
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <span v-for="f in filters" :key="f.value"
              :style="`padding:4px 12px;border-radius:14px;font-size:12px;cursor:pointer;${activeFilter === f.value ? 'background:var(--cuoti-primary);color:#fff' : 'background:var(--cuoti-bg);color:var(--cuoti-text)'}`"
              @click="setFilter(f.value)">
          {{ f.label }}
        </span>
      </div>
    </div>

    <div v-if="questions.length === 0" class="empty">
      <div style="font-size:48px">📭</div>
      <div style="margin-top:12px">暂无题目</div>
    </div>

    <div v-for="q in questions" :key="q.id" class="card" @click="$router.push(`/questions/${q.id}`)">
      <div>
        <span :class="getSubjectTag(q.subject)">{{ q.subject || '未分类' }}</span>
        <span class="tag tag-default">{{ q.knowledge_point || '未标' }}</span>
        <span style="float:right;color:var(--cuoti-text-secondary);font-size:11px">{{ formatDate(q.created_at) }}</span>
      </div>
      <div style="margin-top:6px;font-size:14px;line-height:1.5">
        {{ truncate(q.ocr_text || '[图片题]', 80) }}
      </div>
      <div style="margin-top:6px;font-size:11px;color:var(--cuoti-text-secondary)">
        {{ q.is_correct ? '✅ 已掌握' : '❌ 待复习' }}
        <span v-if="q.is_stubborn" style="color:var(--cuoti-danger);margin-left:6px">🔥 顽固</span>
      </div>
    </div>

    <div class="fab" @click="$router.push('/camera')">📷</div>
    <div class="tab-bar">
      <div class="tab-item" @click="$router.push('/')">首页</div>
      <div class="tab-item active">错题</div>
      <div class="tab-item" @click="$router.push('/reports')">报告</div>
      <div class="tab-item" @click="$router.push('/settings')">设置</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { questionApi, childrenApi } from '../api'

const questions = ref([])
const filters = [
  { label: '全部', value: 'all' },
  { label: '错题', value: 'wrong' },
  { label: '已掌握', value: 'mastered' },
  { label: '顽固', value: 'stubborn' },
]
const activeFilter = ref('all')
let currentChildId = null

const loadQuestions = async () => {
  const params = { child_id: currentChildId, limit: 200 }
  if (activeFilter.value === 'wrong') params.is_correct = false
  if (activeFilter.value === 'mastered') params.review_status = 'mastered'
  if (activeFilter.value === 'stubborn') {
    params.is_correct = false
    params.review_status = 'stubborn'
  }
  const r = await questionApi.list(params)
  questions.value = r.data
}

const setFilter = async (v) => {
  activeFilter.value = v
  await loadQuestions()
}

const getSubjectTag = (s) => {
  const map = { '数学': 'tag-math', '语文': 'tag-chinese', '英语': 'tag-english' }
  return map[s] || 'tag-default'
}

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

const truncate = (s, n) => s.length > n ? s.slice(0, n) + '…' : s

onMounted(async () => {
  const r = await childrenApi.list()
  if (r.data.length === 0) return
  currentChildId = r.data[0].id
  await loadQuestions()
})
</script>
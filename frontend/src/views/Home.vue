<template>
  <div class="page">
    <div class="nav-bar">
      <div class="nav-title" @click="showChildPicker = true">
        {{ currentChild?.name || '选择孩子' }} · {{ currentChild?.grade || '' }} ▼
      </div>
      <van-icon name="setting" size="20" @click="$router.push('/settings')" />
    </div>

    <!-- 数据统计 -->
    <div class="stat-grid" v-if="currentChild">
      <div class="stat-card">
        <div class="stat-num">{{ stats.total }}</div>
        <div class="stat-label">总题数</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="color: var(--cuoti-success)">{{ stats.accuracy_pct }}</div>
        <div class="stat-label">正确率</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="color: var(--cuoti-accent)">{{ stats.stubborn }}</div>
        <div class="stat-label">顽固错题</div>
      </div>
    </div>

    <!-- AI 状态提示 -->
    <div class="card warning-card" v-if="!aiReady.text_ai">
      <div style="font-weight:500;margin-bottom:4px">⚠️ AI 未配置</div>
      <div style="font-size:13px">请到<router-link to="/settings" style="color:var(--cuoti-primary)">设置页</router-link>填入 API Key 后再使用 AI 功能。</div>
    </div>

    <!-- 最近错题 -->
    <div style="margin:16px 12px 8px;font-weight:500">最近错题</div>
    <div v-if="recentQuestions.length === 0" class="empty">
      <div style="font-size:48px">📷</div>
      <div style="margin-top:12px">还没有错题</div>
      <div style="font-size:12px;margin-top:4px">点击下方按钮，拍下第一张错题</div>
    </div>

    <div v-for="q in recentQuestions" :key="q.id" class="card" @click="$router.push(`/questions/${q.id}`)">
      <div>
        <span :class="getSubjectTag(q.subject)">{{ q.subject || '未分类' }}</span>
        <span class="tag tag-default">{{ q.knowledge_point || '未标知识点' }}</span>
        <span style="float:right;color:var(--cuoti-text-secondary);font-size:11px">
          {{ formatDate(q.created_at) }}
        </span>
      </div>
      <div style="margin-top:6px;font-size:14px;line-height:1.5;color:var(--cuoti-text)">
        {{ truncate(q.ocr_text || '[图片题]', 60) }}
      </div>
      <div style="margin-top:6px;font-size:11px;color:var(--cuoti-text-secondary)">
        {{ q.is_correct ? '✅ 已掌握' : '❌ 待复习' }}
        <span v-if="q.is_stubborn" style="color:var(--cuoti-danger);margin-left:8px">🔥 顽固</span>
      </div>
    </div>

    <!-- 浮动拍照按钮 -->
    <div class="fab" @click="$router.push('/camera')">
      📷
    </div>

    <!-- 底部 Tab -->
    <div class="tab-bar">
      <div class="tab-item active" @click="$router.push('/')">首页</div>
      <div class="tab-item" @click="$router.push('/questions')">错题</div>
      <div class="tab-item" @click="$router.push('/reports')">报告</div>
      <div class="tab-item" @click="$router.push('/settings')">设置</div>
    </div>

    <!-- 孩子选择弹窗 -->
    <van-popup v-model:show="showChildPicker" position="bottom" round>
      <div style="padding:16px">
        <div style="font-weight:500;margin-bottom:12px">选择孩子</div>
        <div v-for="c in children" :key="c.id"
             class="card" style="margin:8px 0;cursor:pointer"
             :style="c.id === currentChildId ? 'border:1px solid var(--cuoti-primary)' : ''"
             @click="selectChild(c.id)">
          <div style="display:flex;align-items:center;gap:10px">
            <div :style="`width:36px;height:36px;border-radius:50%;background:${c.avatar_color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:500`">
              {{ c.name[0] }}
            </div>
            <div style="flex:1">
              <div style="font-weight:500">{{ c.name }}</div>
              <div style="font-size:11px;color:var(--cuoti-text-secondary)">{{ c.grade || '未设年级' }} · {{ c.question_count }} 题</div>
            </div>
          </div>
        </div>
        <div class="card" style="cursor:pointer;text-align:center;color:var(--cuoti-primary)" @click="$router.push('/children')">
          + 添加/管理孩子
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { childrenApi, questionApi, statsApi, settingsApi } from '../api'
import { showToast } from 'vant'

const children = ref([])
const currentChildId = ref(null)
const questions = ref([])
const stats = ref({ total: 0, accuracy_pct: '0%', stubborn: 0, mastered: 0 })
const aiReady = ref({ text_ai: false, ocr_ai: false })
const showChildPicker = ref(false)

const currentChild = computed(() => children.value.find(c => c.id === currentChildId.value))
const recentQuestions = computed(() =>
  questions.value.filter(q => !q.is_correct).slice(0, 8)
)

const loadChildren = async () => {
  const r = await childrenApi.list()
  children.value = r.data
  if (currentChildId.value == null && children.value.length > 0) {
    currentChildId.value = children.value[0].id
  } else if (children.value.length === 0) {
    showToast('请先添加孩子')
  }
}

const loadQuestions = async () => {
  if (!currentChildId.value) return
  const r = await questionApi.list({ child_id: currentChildId.value, limit: 50 })
  questions.value = r.data
}

const loadStats = async () => {
  if (!currentChildId.value) return
  const r = await statsApi.summary(currentChildId.value)
  const d = r.data
  stats.value = {
    total: d.total,
    accuracy_pct: d.total > 0 ? Math.round(d.accuracy * 100) + '%' : '-',
    stubborn: d.stubborn,
    mastered: d.mastered,
  }
}

const selectChild = (id) => {
  currentChildId.value = id
  showChildPicker.value = false
  loadQuestions()
  loadStats()
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
  await loadChildren()
  await loadQuestions()
  await loadStats()
  try {
    const r = await settingsApi.status()
    aiReady.value = r.data
  } catch {}
})
</script>
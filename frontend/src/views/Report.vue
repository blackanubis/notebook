<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">学情报告</div>
      <van-icon name="replay" size="20" @click="generate" />
    </div>

    <div v-if="loading" class="empty">
      <van-loading size="36" color="#185FA5" />
      <div style="margin-top:12px">AI 正在生成报告...</div>
    </div>

    <template v-else-if="report">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-num">{{ report.total_questions }}</div>
          <div class="stat-label">总题数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color:var(--cuoti-success)">
            {{ Math.round(report.accuracy_rate * 100) }}%
          </div>
          <div class="stat-label">正确率</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color:var(--cuoti-accent)">{{ report.stubborn_count }}</div>
          <div class="stat-label">顽固</div>
        </div>
      </div>

      <div class="card">
        <div style="font-weight:500;margin-bottom:6px">📝 总结</div>
        <div style="line-height:1.6;font-size:13px">{{ report.summary }}</div>
      </div>

      <div class="card success-card" v-if="parseList(report.strengths).length">
        <div style="font-weight:500;margin-bottom:6px">🌟 优势领域</div>
        <div v-for="s in parseList(report.strengths)" :key="s.kp" style="font-size:13px;margin:4px 0">
          · {{ s.kp }}（{{ Math.round((s.rate || 0) * 100) }}%）
        </div>
      </div>

      <div class="card error-card" v-if="parseList(report.weaknesses).length">
        <div style="font-weight:500;margin-bottom:6px">🔴 待提升</div>
        <div v-for="w in parseList(report.weaknesses)" :key="w.kp" style="font-size:13px;margin:4px 0">
          · {{ w.kp }}（{{ Math.round((w.rate || 0) * 100) }}%）
        </div>
      </div>

      <div class="card warning-card" v-if="parseList(report.improvements).length">
        <div style="font-weight:500;margin-bottom:6px">🚀 进步</div>
        <div v-for="i in parseList(report.improvements)" :key="i.kp" style="font-size:13px;margin:4px 0">
          · {{ i.kp }}（{{ Math.round((i.from || 0) * 100) }}% → {{ Math.round((i.to || 0) * 100) }}%）
        </div>
      </div>

      <div class="card" v-if="parseList(report.suggestions).length">
        <div style="font-weight:500;margin-bottom:6px">💡 给家长的建议</div>
        <div v-for="(s, i) in parseList(report.suggestions)" :key="i" style="font-size:13px;margin:6px 0;line-height:1.5">
          {{ i + 1 }}. {{ s }}
        </div>
      </div>

      <div class="btn-row">
        <van-button block round type="primary" @click="generate">🔄 重新生成</van-button>
      </div>
    </template>

    <div v-else class="empty">
      <div style="font-size:48px">📊</div>
      <div style="margin-top:12px">本周暂无报告</div>
      <van-button round type="primary" style="margin-top:14px" @click="generate">生成本周报告</van-button>
    </div>

    <div class="tab-bar">
      <div class="tab-item" @click="$router.push('/')">首页</div>
      <div class="tab-item" @click="$router.push('/questions')">错题</div>
      <div class="tab-item active">报告</div>
      <div class="tab-item" @click="$router.push('/settings')">设置</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { reportApi, childrenApi } from '../api'
import { showToast } from 'vant'

const report = ref(null)
const loading = ref(false)
let currentChildId = null

const parseList = (s) => {
  try {
    if (Array.isArray(s)) return s
    return JSON.parse(s || '[]')
  } catch { return [] }
}

const loadLatest = async () => {
  const r = await reportApi.list(currentChildId)
  if (r.data.length > 0) report.value = r.data[0]
}

const generate = async () => {
  if (!currentChildId) return
  loading.value = true
  try {
    const r = await reportApi.generate(currentChildId, 'weekly')
    const detail = (await reportApi.get(r.data.report_id)).data
    report.value = detail
    showToast('报告已生成')
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const r = await childrenApi.list()
  if (r.data.length > 0) {
    currentChildId = r.data[0].id
    await loadLatest()
  }
})
</script>
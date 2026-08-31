<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">导出练习</div>
      <span style="width:20px"></span>
    </div>

    <div class="card">
      <div style="font-weight:500;margin-bottom:8px">选择模板</div>
      <van-radio-group v-model="template">
        <van-radio name="questions_only">仅题目（孩子自测）</van-radio>
        <van-radio name="with_answers">题目+答案（家长版）</van-radio>
        <van-radio name="with_answer_sheet">题目+答题卡</van-radio>
      </van-radio-group>
    </div>

    <div class="card">
      <div style="font-weight:500;margin-bottom:8px">题目（已选）</div>
      <div v-if="questions.length === 0" class="empty" style="padding:20px">暂无可导出题目</div>
      <div v-for="q in questions" :key="q.id" style="padding:10px;border-bottom:0.5px solid var(--cuoti-bg)">
        <span class="tag tag-default">{{ q.knowledge_point || '未标' }}</span>
        <span style="font-size:13px;margin-left:6px">{{ truncate(q.ocr_text || '[图片题]', 40) }}</span>
      </div>
    </div>

    <div class="btn-row">
      <van-button block round type="primary" :loading="loading" @click="exportPDF">
        📥 生成 PDF
      </van-button>
    </div>

    <div v-if="pdfUrl" class="card success-card">
      <div style="font-weight:500;margin-bottom:8px">✅ PDF 已生成</div>
      <a :href="pdfUrl" target="_blank" style="display:block;color:var(--cuoti-primary);text-decoration:underline">
        📥 点击下载 PDF
      </a>
      <van-button block size="small" style="margin-top:8px" @click="window.print()">
        🖨 调用系统打印
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { questionApi, exportApi, childrenApi } from '../api'

const route = useRoute()
const template = ref('questions_only')
const questions = ref([])
const pdfUrl = ref('')
const loading = ref(false)
let currentChildId = null

const loadQuestions = async () => {
  const r = await questionApi.list({ child_id: currentChildId, is_correct: false, limit: 50 })
  // 如果是从单题进入，只导出该题
  if (route.params.id && route.params.id !== 'all') {
    const one = (await questionApi.get(route.params.id)).data
    questions.value = [one]
  } else {
    questions.value = r.data.slice(0, 5)
  }
}

const exportPDF = async () => {
  if (questions.value.length === 0) return
  loading.value = true
  try {
    const r = await exportApi.pdf({
      question_ids: questions.value.map(q => q.id),
      template: template.value,
      child_id: currentChildId,
    })
    pdfUrl.value = r.data.pdf_url
  } finally {
    loading.value = false
  }
}

const truncate = (s, n) => s.length > n ? s.slice(0, n) + '…' : s

onMounted(async () => {
  const r = await childrenApi.list()
  if (r.data.length > 0) {
    currentChildId = r.data[0].id
    await loadQuestions()
  }
})
</script>
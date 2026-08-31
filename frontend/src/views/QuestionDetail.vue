<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">错题详情</div>
      <van-icon name="edit" size="20" @click="showEdit = true" />
    </div>

    <div v-if="!question" class="empty">加载中...</div>

    <template v-else>
      <!-- 题目信息 -->
      <div class="card">
        <div>
          <span :class="getSubjectTag(question.subject)">{{ question.subject || '未分类' }}</span>
          <span class="tag tag-default">{{ question.knowledge_point || '未标' }}</span>
        </div>
        <div v-if="question.image_url" style="margin-top:10px">
          <img :src="question.image_url" style="max-width:100%;border-radius:6px" />
        </div>
        <div class="q-text" style="margin-top:10px">{{ question.ocr_text || '（暂无题目文本）' }}</div>
        <div v-if="question.student_answer" style="margin-top:8px;padding:8px;background:var(--cuoti-bg);border-radius:6px;font-size:13px">
          <span style="color:var(--cuoti-text-secondary)">学生答案：</span>
          {{ question.student_answer }}
        </div>
      </div>

      <!-- AI 错因诊断 -->
      <div class="card error-card">
        <div style="font-weight:500;margin-bottom:6px">✦ AI 错因诊断</div>
        <div v-if="loadingAI" style="text-align:center;padding:20px">
          <van-loading size="24" color="#993C1D" />
          <div style="font-size:12px;margin-top:6px">AI 分析中...</div>
        </div>
        <template v-else-if="question.error_reason">
          <div style="margin-bottom:8px">
            <span class="tag" style="background:var(--cuoti-danger-light);color:var(--cuoti-danger)">
              {{ getErrorTypeLabel(question.error_type) }}
            </span>
            <span class="tag tag-default">{{ question.knowledge_point || '未标知识点' }}</span>
          </div>
          <div style="line-height:1.6;font-size:13px">{{ question.error_reason }}</div>
        </template>
        <van-button v-else block round plain size="small" @click="runAnalysis" style="margin-top:8px">
          🔍 AI 错因分析
        </van-button>
      </div>

      <!-- 标准答案 -->
      <div v-if="question.correct_answer" class="card success-card">
        <div style="font-weight:500;margin-bottom:6px">✅ 标准答案</div>
        <div class="markdown">{{ question.correct_answer }}</div>
      </div>

      <!-- 步骤详解 -->
      <div v-if="question.solution_steps" class="card">
        <div style="font-weight:500;margin-bottom:6px">📝 解答步骤</div>
        <div class="markdown">{{ question.solution_steps }}</div>
      </div>

      <!-- 操作按钮 -->
      <div class="btn-row" style="margin-top:20px">
        <van-button block round type="primary" @click="$router.push(`/practice/${question.id}`)">
          🎯 看相似题
        </van-button>
        <van-button block round plain @click="$router.push(`/export/${question.id}`)">
          📥 导出练习
        </van-button>
      </div>
      <div class="btn-row">
        <van-button block round size="small" @click="markMastered" :disabled="question.is_correct">
          ✓ 标记已掌握
        </van-button>
        <van-button block round size="small" plain @click="confirmDelete" style="color:var(--cuoti-danger);border-color:var(--cuoti-danger)">
          删除
        </van-button>
      </div>
    </template>

    <!-- 编辑弹窗 -->
    <van-popup v-model:show="showEdit" position="bottom" round style="height:80%">
      <div style="padding:16px;height:100%;overflow:auto">
        <div style="font-weight:500;margin-bottom:12px">编辑题目</div>
        <van-field v-model="editForm.ocr_text" type="textarea" rows="3" autosize label="题目" />
        <van-field v-model="editForm.student_answer" type="textarea" rows="2" autosize label="学生答案" />
        <van-field v-model="editForm.knowledge_point" label="知识点" placeholder="如：分数应用题" />
        <van-field v-model="editForm.subject" label="学科" placeholder="如：数学" />
        <div style="margin-top:14px;display:flex;gap:10px">
          <van-button block @click="showEdit = false">取消</van-button>
          <van-button block type="primary" @click="saveEdit">保存</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { questionApi, aiApi } from '../api'
import { showSuccessToast, showConfirmDialog } from 'vant'

const route = useRoute()
const router = useRouter()
const question = ref(null)
const loadingAI = ref(false)
const showEdit = ref(false)
const editForm = ref({})

const loadQuestion = async () => {
  const r = await questionApi.get(route.params.id)
  question.value = r.data
  editForm.value = {
    ocr_text: r.data.ocr_text,
    student_answer: r.data.student_answer,
    knowledge_point: r.data.knowledge_point,
    subject: r.data.subject,
  }
}

const runAnalysis = async () => {
  if (!question.value) return
  loadingAI.value = true
  try {
    const r = await aiApi.analyzeError({
      question_text: question.value.ocr_text || '[图片题]',
      student_answer: question.value.student_answer || '',
      subject: question.value.subject || '数学',
      knowledge_point: question.value.knowledge_point || '',
    })
    const d = r.data
    await questionApi.update(question.value.id, {
      error_reason: d.error_reason,
      correct_answer: d.correct_answer,
      solution_steps: d.solution_steps,
      error_type: d.error_type,
      knowledge_point: d.knowledge_point,
      subject: question.value.subject || d.knowledge_point || '',
    })
    await loadQuestion()
    showSuccessToast('AI 分析完成')
  } catch (e) {
    console.error(e)
  } finally {
    loadingAI.value = false
  }
}

const markMastered = async () => {
  await questionApi.update(question.value.id, { review_status: 'mastered', is_correct: true })
  showSuccessToast('已标记掌握')
  await loadQuestion()
}

const saveEdit = async () => {
  await questionApi.update(question.value.id, editForm.value)
  showEdit.value = false
  await loadQuestion()
  showSuccessToast('已保存')
}

const confirmDelete = async () => {
  try {
    await showConfirmDialog({ title: '确认删除', message: '删除后无法恢复' })
    await questionApi.remove(question.value.id)
    showSuccessToast('已删除')
    router.back()
  } catch {}
}

const getSubjectTag = (s) => {
  const map = { '数学': 'tag-math', '语文': 'tag-chinese', '英语': 'tag-english' }
  return map[s] || 'tag-default'
}

const getErrorTypeLabel = (t) => {
  const map = {
    concept: '概念不清', calculation: '计算错误',
    misread: '审题失误', method: '方法不当', careless: '粗心大意',
  }
  return map[t] || '其他'
}

onMounted(loadQuestion)
</script>
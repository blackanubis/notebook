<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">相似题 {{ current + 1 }}/{{ questions.length }}</div>
      <span style="width:20px"></span>
    </div>

    <div v-if="questions.length === 0" class="empty">
      <div style="font-size:48px">⏳</div>
      <div style="margin-top:12px">AI 正在生成相似题...</div>
    </div>

    <template v-else-if="!showResult">
      <div class="card">
        <div class="q-text">{{ questions[current].question }}</div>
      </div>
      <div class="card">
        <div style="font-weight:500;margin-bottom:6px">你的答案</div>
        <van-field v-model="studentAnswer" type="textarea" rows="4" autosize placeholder="在此输入或拍照..." />
        <input ref="fileInput" type="file" accept="image/*" capture="environment" style="display:none" @change="onPhotoAnswer" />
        <van-button block plain size="small" style="margin-top:8px" @click="$refs.fileInput.click()">
          📷 拍照作答
        </van-button>
        <div v-if="photoUrl" style="margin-top:8px">
          <img :src="photoUrl" style="max-width:100%;border-radius:6px" />
        </div>
      </div>
      <div class="btn-row">
        <van-button block @click="skip">跳过</van-button>
        <van-button block type="primary" :loading="judging" @click="submit">提交评判</van-button>
      </div>
    </template>

    <template v-else>
      <div class="card" style="text-align:center">
        <div :style="`font-size:48px;font-weight:500;color:${result.score >= 60 ? 'var(--cuoti-success)' : 'var(--cuoti-danger)'}`">
          {{ result.score }}
        </div>
        <div style="font-size:12px;color:var(--cuoti-text-secondary);margin-top:4px">分</div>
      </div>

      <div class="card" v-if="result.error_point && result.score < 100">
        <div style="font-weight:500;color:var(--cuoti-danger);margin-bottom:6px">⚠ 扣分点</div>
        <div>{{ result.error_point }}</div>
      </div>

      <div class="card success-card">
        <div style="font-weight:500;margin-bottom:6px">📝 详细评判</div>
        <div class="markdown">{{ result.ai_judgment }}</div>
      </div>

      <div class="card">
        <div style="font-weight:500;margin-bottom:6px">✅ 标准答案</div>
        <div class="markdown">{{ questions[current].answer }}</div>
      </div>

      <div class="btn-row">
        <van-button block @click="next">下一题</van-button>
        <van-button block type="primary" @click="$router.back()">完成</van-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { questionApi, aiApi, uploadApi, practiceApi } from '../api'
import { showSuccessToast } from 'vant'

const route = useRoute()
const questions = ref([])
const current = ref(0)
const studentAnswer = ref('')
const photoUrl = ref('')
const photoFile = ref(null)
const judging = ref(false)
const result = ref(null)
const showResult = ref(false)

const generate = async () => {
  const q = (await questionApi.get(route.params.id)).data
  if (!q.correct_answer) {
    alert('请先在错题详情页运行 AI 错因分析')
    return
  }
  const r = await aiApi.similarQuestions({
    question_text: q.ocr_text || '[图片题]',
    correct_answer: q.correct_answer,
    subject: q.subject || '数学',
    knowledge_point: q.knowledge_point || '',
    count: 5,
  })
  questions.value = r.data.questions
}

const onPhotoAnswer = (e) => {
  const file = e.target.files[0]
  if (!file) return
  photoFile.value = file
  photoUrl.value = URL.createObjectURL(file)
}

const submit = async () => {
  judging.value = true
  try {
    let imageUrl = ''
    if (photoFile.value) {
      const r = await uploadApi.image(photoFile.value)
      imageUrl = r.data.url
    }
    const r = await aiApi.judge({
      practice_question: questions.value[current.value].question,
      practice_answer: questions.value[current.value].answer,
      student_response: studentAnswer.value + (imageUrl ? `\n[图片作答：${imageUrl}]` : ''),
      subject: '数学',
    })
    result.value = r.data
    showResult.value = true
    // 保存练习
    await practiceApi.save({
      question_id: parseInt(route.params.id),
      practice_question: questions.value[current.value].question,
      practice_answer: questions.value[current.value].answer,
      student_response: studentAnswer.value,
      score: r.data.score,
      is_correct: r.data.is_correct,
      error_point: r.data.error_point,
      ai_judgment: r.data.ai_judgment,
    })
  } catch (e) {
    console.error(e)
  } finally {
    judging.value = false
  }
}

const next = () => {
  if (current.value < questions.value.length - 1) {
    current.value++
    studentAnswer.value = ''
    photoUrl.value = ''
    photoFile.value = null
    showResult.value = false
    result.value = null
  } else {
    showSuccessToast('已完成全部练习')
    // 返回
  }
}

const skip = () => next()

onMounted(generate)
</script>
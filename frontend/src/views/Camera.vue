<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">拍照录入</div>
      <span style="width:20px"></span>
    </div>

    <!-- 步骤指示 -->
    <div style="display:flex;gap:6px;padding:12px">
      <div :style="`flex:1;padding:6px;border-radius:6px;text-align:center;font-size:12px;font-weight:500;${step>=1?'background:var(--cuoti-primary);color:#fff':'background:var(--cuoti-card);color:var(--cuoti-text-secondary)'}`">① 拍照</div>
      <div :style="`flex:1;padding:6px;border-radius:6px;text-align:center;font-size:12px;font-weight:500;${step>=2?'background:var(--cuoti-primary);color:#fff':'background:var(--cuoti-card);color:var(--cuoti-text-secondary)'}`">② 识别</div>
      <div :style="`flex:1;padding:6px;border-radius:6px;text-align:center;font-size:12px;font-weight:500;${step>=3?'background:var(--cuoti-primary);color:#fff':'background:var(--cuoti-card);color:var(--cuoti-text-secondary)'}`">③ 标注</div>
    </div>

    <!-- Step 1: 拍照 -->
    <div v-if="step === 1" class="card" style="margin-top:20px">
      <div style="text-align:center;padding:40px 20px;background:var(--cuoti-bg);border-radius:8px;border:1px dashed #B4B2A9">
        <div style="font-size:48px;color:var(--cuoti-primary)">📷</div>
        <div style="margin-top:12px;font-size:14px">拍下错题/试卷</div>
        <div style="font-size:12px;color:var(--cuoti-text-secondary);margin-top:4px">支持整页试卷自动切题</div>
      </div>
      <div style="margin-top:14px">
        <input ref="fileInput" type="file" accept="image/*" capture="environment" style="display:none" @change="onFileChange" />
        <van-button block round type="primary" @click="openCamera">
          📷 拍 照
        </van-button>
        <van-button block round plain style="margin-top:8px" @click="openGallery">
          🖼 从相册选
        </van-button>
      </div>
      <div v-if="previewUrl" style="margin-top:14px">
        <img :src="previewUrl" style="max-width:100%;border-radius:8px" />
      </div>
    </div>

    <!-- Step 2: 识别中 -->
    <div v-if="step === 2" class="card" style="text-align:center;padding:60px 20px">
      <van-loading type="spinner" size="36" color="#185FA5" />
      <div style="margin-top:16px">AI 正在识别题目...</div>
      <div style="font-size:12px;color:var(--cuoti-text-secondary);margin-top:6px">可能需要 5~15 秒</div>
    </div>

    <!-- Step 3: 标注对错 -->
    <div v-if="step === 3" style="padding-bottom:80px">
      <div class="card" style="background:var(--cuoti-warning-light);border-color:var(--cuoti-warning)">
        <div style="font-size:12px">💡 识别结果可能不完美，请逐题核对文字并标记对/错</div>
      </div>

      <div v-for="(item, idx) in recognizedQuestions" :key="idx" class="card">
        <div style="font-size:12px;color:var(--cuoti-text-secondary);margin-bottom:6px">
          第 {{ idx + 1 }} 题
        </div>
        <van-field
          v-model="item.text"
          type="textarea"
          rows="3"
          autosize
          placeholder="题目文本"
          style="margin-bottom:10px"
        />
        <div style="display:flex;gap:8px">
          <van-button :type="item.is_correct ? 'success' : 'default'"
                      :plain="!item.is_correct" block @click="item.is_correct = true">
            ✓ 对
          </van-button>
          <van-button :type="!item.is_correct ? 'danger' : 'default'"
                      :plain="item.is_correct" block @click="item.is_correct = false">
            ✗ 错
          </van-button>
        </div>
      </div>

      <div style="padding:14px">
        <van-button block round type="primary" :loading="saving" @click="saveAll">
          完 成 录 入
        </van-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { uploadApi, ocrApi, questionApi, childrenApi } from '../api'
import { showToast, showSuccessToast } from 'vant'

const router = useRouter()
const fileInput = ref(null)
const step = ref(1)
const previewUrl = ref('')
const imageUrl = ref('')
const recognizedQuestions = ref([])
const saving = ref(false)
let currentChildId = null

const openCamera = () => {
  fileInput.value.click()
}

const openGallery = () => {
  if (fileInput.value) fileInput.value.removeAttribute('capture')
  fileInput.value.click()
}

const onFileChange = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 20 * 1024 * 1024) {
    showToast('图片不能超过 20MB')
    return
  }
  previewUrl.value = URL.createObjectURL(file)
  step.value = 2

  try {
    // 1. 上传图片
    const r = await uploadApi.image(file)
    imageUrl.value = r.data.url

    // 2. 获取孩子 ID
    const cr = await childrenApi.list()
    if (cr.data.length === 0) {
      showToast('请先添加孩子')
      router.push('/children')
      return
    }
    currentChildId = cr.data[0].id

    // 3. 调用 OCR
    const or = await ocrApi.recognize({ image_url: imageUrl.value, child_id: currentChildId })
    recognizedQuestions.value = or.data.questions.map(q => ({
      text: q.text,
      subject_hint: q.subject_hint,
      is_correct: false,
    }))
    if (recognizedQuestions.value.length === 0) {
      showToast('未识别到题目，请手动录入')
      recognizedQuestions.value = [{ text: '', subject_hint: '', is_correct: false }]
    }
    if (or.data.note) showToast(or.data.note)
    step.value = 3
  } catch (err) {
    console.error(err)
    step.value = 1
  }
}

const saveAll = async () => {
  if (!currentChildId) return
  saving.value = true
  try {
    for (const q of recognizedQuestions.value) {
      if (!q.text.trim()) continue
      await questionApi.create({
        child_id: currentChildId,
        image_url: imageUrl.value,
        ocr_text: q.text,
        is_correct: q.is_correct,
        subject: q.subject_hint || '',
        source: 'photo',
      })
    }
    showSuccessToast('录入完成')
    setTimeout(() => router.push('/'), 800)
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

onMounted(() => {})
</script>
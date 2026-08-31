<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">AI 设置</div>
      <span style="width:20px"></span>
    </div>

    <div class="card" style="background:var(--cuoti-warning-light);border-color:var(--cuoti-warning)">
      <div style="font-size:13px;line-height:1.5">
        💡 这里分别配置两类 AI：
        <br/>· <b>通用 AI</b>：错因诊断、相似题出题、评判、报告
        <br/>· <b>OCR AI</b>：图片题目识别（视觉模型）
        <br/>推荐使用 minimax 的对应模型，可在不同模型间切换。
      </div>
    </div>

    <!-- 通用 AI -->
    <div class="card">
      <div style="font-weight:500;margin-bottom:10px">🧠 通用 AI（文本）</div>
      <van-field v-model="form.text_api_key" label="API Key" placeholder="sk-xxx" type="password" />
      <van-field v-model="form.text_base_url" label="Base URL" placeholder="https://api.minimax.chat/v1" />
      <van-field v-model="form.text_model" label="模型" placeholder="MiniMax-Text-01" />
    </div>

    <!-- OCR AI -->
    <div class="card">
      <div style="font-weight:500;margin-bottom:10px">📷 OCR AI（视觉）</div>
      <van-field v-model="form.ocr_api_key" label="API Key" placeholder="sk-xxx" type="password" />
      <van-field v-model="form.ocr_base_url" label="Base URL" placeholder="https://api.minimax.chat/v1" />
      <van-field v-model="form.ocr_model" label="模型" placeholder="MiniMax-VL-01" />
    </div>

    <!-- 推送 -->
    <div class="card">
      <div style="font-weight:500;margin-bottom:10px">📨 推送（可选）</div>
      <van-field v-model="form.pushplus_token" label="PushPlus" placeholder="微信推送 Token" />
      <van-field v-model="form.notify_email" label="邮箱" placeholder="家长邮箱" />
    </div>

    <div class="btn-row">
      <van-button block round type="primary" :loading="saving" @click="save">保 存</van-button>
    </div>

    <div v-if="savedTip" class="card success-card" style="text-align:center">
      ✅ 已保存
    </div>

    <div class="tab-bar">
      <div class="tab-item" @click="$router.push('/')">首页</div>
      <div class="tab-item" @click="$router.push('/questions')">错题</div>
      <div class="tab-item" @click="$router.push('/reports')">报告</div>
      <div class="tab-item active">设置</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { settingsApi } from '../api'
import { showSuccessToast } from 'vant'

const form = ref({
  text_api_key: '', text_base_url: '', text_model: '',
  ocr_api_key: '', ocr_base_url: '', ocr_model: '',
  pushplus_token: '', notify_email: '',
})
const saving = ref(false)
const savedTip = ref(false)

const load = async () => {
  const r = await settingsApi.getAI()
  Object.assign(form.value, r.data)
}

const save = async () => {
  saving.value = true
  try {
    await settingsApi.updateAI(form.value)
    showSuccessToast('已保存')
    savedTip.value = true
    setTimeout(() => savedTip.value = false, 2000)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
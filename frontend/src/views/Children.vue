<template>
  <div class="page">
    <div class="nav-bar">
      <van-icon name="arrow-left" size="20" @click="$router.back()" />
      <div class="nav-title">孩子管理</div>
      <van-icon name="plus" size="20" @click="showAdd = true" />
    </div>

    <div v-for="c in children" :key="c.id" class="card">
      <div style="display:flex;align-items:center;gap:12px">
        <div :style="`width:48px;height:48px;border-radius:50%;background:${c.avatar_color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:500;font-size:18px`">
          {{ c.name[0] }}
        </div>
        <div style="flex:1">
          <div style="font-weight:500">{{ c.name }}</div>
          <div style="font-size:11px;color:var(--cuoti-text-secondary)">{{ c.grade }} · {{ c.textbook_version }} · {{ c.question_count }} 题</div>
        </div>
        <van-icon name="edit" @click="edit(c)" />
        <van-icon name="delete-o" @click="remove(c)" style="color:var(--cuoti-danger);margin-left:8px" />
      </div>
    </div>

    <van-popup v-model:show="showAdd" position="bottom" round style="height:auto">
      <div style="padding:16px">
        <div style="font-weight:500;margin-bottom:12px">{{ editing ? '编辑' : '添加' }}孩子</div>
        <van-field v-model="form.name" label="姓名" placeholder="如：小明" />
        <van-field v-model="form.grade" label="年级" placeholder="如：三年级" />
        <van-field v-model="form.textbook_version" label="教材版本" placeholder="人教版/北师大版" />
        <div style="margin-top:14px;display:flex;gap:10px">
          <van-button block @click="showAdd = false">取消</van-button>
          <van-button block type="primary" @click="save">保存</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { childrenApi } from '../api'
import { showSuccessToast, showConfirmDialog } from 'vant'

const children = ref([])
const showAdd = ref(false)
const editing = ref(null)
const form = ref({ name: '', grade: '', textbook_version: '人教版', avatar_color: '#185FA5' })

const load = async () => {
  const r = await childrenApi.list()
  children.value = r.data
}

const edit = (c) => {
  editing.value = c.id
  form.value = { name: c.name, grade: c.grade, textbook_version: c.textbook_version, avatar_color: c.avatar_color }
  showAdd.value = true
}

const save = async () => {
  if (!form.value.name.trim()) return
  if (editing.value) {
    await childrenApi.update(editing.value, form.value)
  } else {
    await childrenApi.create(form.value)
  }
  showAdd.value = false
  editing.value = null
  form.value = { name: '', grade: '', textbook_version: '人教版', avatar_color: '#185FA5' }
  showSuccessToast('已保存')
  await load()
}

const remove = async (c) => {
  try {
    await showConfirmDialog({ title: '删除', message: `确认删除 ${c.name}？所有错题也会删除` })
    await childrenApi.remove(c.id)
    await load()
    showSuccessToast('已删除')
  } catch {}
}

onMounted(load)
</script>
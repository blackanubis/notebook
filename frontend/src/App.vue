<template>
  <router-view />
</template>

<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'
const route = useRoute()
const title = computed(() => route.meta.title || '家庭错题本')
</script>
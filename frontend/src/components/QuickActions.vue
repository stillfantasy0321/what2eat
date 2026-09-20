<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ busy: boolean; categories: string[] }>()
const emit = defineEmits<{ send: [prompt: string] }>()
const choosingCategory = ref(false)
const category = ref('')

const prompts = {
  all: '获取所有菜谱',
  decide: '按 1 人晚餐为我推荐今天吃什么',
  week: '按 1 人、7 天、每天三餐生成不重复的膳食计划',
}

function chooseCategory() {
  choosingCategory.value = true
  if (!category.value) category.value = '早餐'
}

function sendCategory() {
  if (!category.value) return
  emit('send', `获取“${category.value}”分类菜谱并简要介绍。`)
  choosingCategory.value = false
}
</script>

<template>
  <section class="quick-actions" aria-label="Agent 快捷功能">
    <header><span>QUICK START</span><h2>想怎么吃？</h2><p>选一个入口，Agent 会直接翻阅菜谱。</p></header>
    <div class="quick-grid">
      <button data-quick-action="all" :disabled="busy" @click="emit('send', prompts.all)"><b>01</b><strong>获取所有菜谱</strong><small>get_all_recipes</small></button>
      <button data-quick-action="category" :disabled="busy" @click="chooseCategory"><b>02</b><strong>按分类获取菜谱</strong><small>get_recipes_by_category</small></button>
      <button data-quick-action="decide" :disabled="busy" @click="emit('send', prompts.decide)"><b>03</b><strong>不知道吃什么</strong><small>what_to_eat</small></button>
      <button data-quick-action="week" :disabled="busy" @click="emit('send', prompts.week)"><b>04</b><strong>推荐膳食计划</strong><small>recommend_meals</small></button>
    </div>
    <form v-if="choosingCategory" class="quick-form" @submit.prevent="sendCategory">
      <label>选择分类<select v-model="category" aria-label="菜谱分类"><option v-for="item in categories" :key="item" :value="item">{{ item }}</option><option v-if="!categories.length" value="早餐">早餐</option></select></label>
      <button type="submit" data-action="send-category" :disabled="busy || !category">查这一类</button>
    </form>
  </section>
</template>

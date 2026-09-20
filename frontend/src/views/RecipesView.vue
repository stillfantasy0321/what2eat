<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { Recipe } from '../api/types'
import PaginationBar from '../components/PaginationBar.vue'
import RecipeCard from '../components/RecipeCard.vue'
import RecipeModal from '../components/RecipeModal.vue'
import { useRecipes } from '../composables/useRecipes'

const recipes = useRecipes()
const uploadBusy = ref(false)
const uploadError = ref('')
const uploadNotice = ref('')
const modal = ref({
  open: false, title: '', markdown: '', sourceUrl: null as string | null,
  busy: false, error: '',
})

function selectCategory(value: string) {
  recipes.activeCategory.value = value
  recipes.load({ category: value, page: 1 })
}

function openRecipe(recipe: Recipe) {
  modal.value = {
    open: true, title: recipe.title, markdown: recipe.raw_text,
    sourceUrl: recipe.source_url ?? null, busy: false, error: '',
  }
}

async function upload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadBusy.value = true
  uploadError.value = ''
  uploadNotice.value = ''
  const form = new FormData()
  form.append('file', file)
  try {
    await api('/api/documents', { method: 'POST', body: form })
    uploadNotice.value = '菜谱已上传，后台完成索引后会出现在列表中。'
    await recipes.load({ category: recipes.activeCategory.value, page: 1 })
  } catch (reason) {
    uploadError.value = reason instanceof Error ? reason.message : '上传失败'
  } finally {
    uploadBusy.value = false
    input.value = ''
  }
}

onMounted(() => recipes.load({ page: 1 }))
</script>

<template>
  <div class="recipe-workspace">
    <header class="workspace-head">
      <div class="workspace-title">
        <span class="eyebrow">WHAT2EAT LIBRARY</span>
        <h1>菜谱</h1>
        <small v-if="recipes.total.value">{{ recipes.total.value }} 道可做菜谱</small>
      </div>
      <label class="file-button workspace-upload" :class="{ busy: uploadBusy }">
        <span>{{ uploadBusy ? '上传中…' : '上传菜谱' }}</span>
        <input type="file" accept=".md,.txt,.pdf,.docx" :disabled="uploadBusy" @change="upload">
      </label>
    </header>

    <p v-if="uploadError" class="error">{{ uploadError }}</p>
    <p v-else-if="uploadNotice" class="notice">{{ uploadNotice }}</p>

    <section class="recipes-pane">
      <div class="category-tabs" aria-label="菜谱分类">
        <button data-category="all" :class="{ active: !recipes.activeCategory.value }" @click="selectCategory('')">全部</button>
        <button v-for="item in recipes.categories.value" :key="item" :data-category="item"
                :class="{ active: recipes.activeCategory.value === item }" @click="selectCategory(item)">{{ item }}</button>
      </div>
      <p v-if="recipes.error.value" class="error">{{ recipes.error.value }}</p>
      <div v-else-if="!recipes.loading.value && !recipes.recipes.value.length" class="empty-panel">
        还没有可用菜谱，请上传菜谱资料。
      </div>
      <div class="recipe-grid">
        <RecipeCard v-for="recipe in recipes.recipes.value" :key="recipe.id" :recipe="recipe" @select="openRecipe" />
      </div>
      <PaginationBar :page="recipes.page.value" :total-pages="recipes.totalPages.value"
                     :busy="recipes.loading.value" @change="recipes.load({ page: $event })" />
    </section>

    <RecipeModal v-bind="modal" @close="modal.open = false" />
  </div>
</template>
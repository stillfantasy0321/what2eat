<script setup lang="ts">
import type { Recipe } from '../api/types'
defineProps<{ recipe: Recipe; deleting?: boolean }>()
defineEmits<{ select: [recipe: Recipe]; remove: [recipe: Recipe] }>()
</script>
<template>
  <article class="recipe-card">
    <button type="button" class="recipe-card-open" :aria-label="`打开菜谱 ${recipe.title}`" @click="$emit('select', recipe)">
      <span class="recipe-index" aria-hidden="true">RECIPE</span>
      <div>
        <small>{{ recipe.category }}</small>
        <h3>{{ recipe.title }}</h3>
        <p>{{ recipe.ingredients.slice(0, 4).map(i => i.name).join('、') || '打开原文了解食材' }}</p>
      </div>
      <span class="read-link">阅读原文 <span aria-hidden="true">→</span></span>
    </button>
    <button type="button" class="recipe-delete" :disabled="deleting"
            :aria-label="`删除菜谱 ${recipe.title}`" @click="$emit('remove', recipe)">
      {{ deleting ? '删除中…' : '删除' }}
    </button>
  </article>
</template>

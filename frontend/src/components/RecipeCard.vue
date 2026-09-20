<script setup lang="ts">
import type { Recipe } from '../api/types'
defineProps<{ recipe: Recipe }>()
defineEmits<{ select: [recipe: Recipe] }>()
</script>
<template><button type="button" class="recipe-card" @click="$emit('select', recipe)"><span class="recipe-index" aria-hidden="true">RECIPE</span><div><small>{{ recipe.category }}</small><h3>{{ recipe.title }}</h3><p>{{ recipe.ingredients.slice(0, 4).map(i => i.name).join('、') || '打开原文了解食材' }}</p></div><span class="read-link">阅读原文 <span aria-hidden="true">→</span></span></button></template>

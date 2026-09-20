<script setup lang="ts">
import { computed } from 'vue'
import { cleanRecipeMarkdown, renderMarkdown } from '../lib/markdown'

const props = defineProps<{
  open: boolean
  title: string
  markdown: string
  sourceUrl?: string | null
  busy?: boolean
  error?: string
}>()
defineEmits<{ close: [] }>()

const html = computed(() => renderMarkdown(cleanRecipeMarkdown(props.markdown)))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="$emit('close')">
    <section class="recipe-modal" role="dialog" aria-modal="true" :aria-label="title">
      <header class="recipe-modal-head">
        <div>
          <span class="drawer-kicker">ORIGINAL RECIPE</span>
          <h2>{{ title }}</h2>
        </div>
        <button type="button" class="modal-close" aria-label="关闭菜谱" @click="$emit('close')">×</button>
      </header>
      <div class="recipe-modal-body">
        <p v-if="busy" class="drawer-loading">正在打开原文…</p>
        <p v-else-if="error" class="error">{{ error }}</p>
        <article v-else class="markdown-body" v-html="html" />
      </div>
      <footer v-if="sourceUrl" class="recipe-modal-foot">
        <a class="source-link" :href="sourceUrl" target="_blank" rel="noopener noreferrer">
          打开原始来源 <span aria-hidden="true">↗</span>
        </a>
      </footer>
    </section>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { cleanRecipeMarkdown, renderMarkdown } from '../lib/markdown'

const props = defineProps<{
  open: boolean
  title: string
  markdown: string
  sourceUrl?: string | null
  busy?: boolean
  error?: string
  deleting?: boolean
  deleteError?: string
}>()
const emit = defineEmits<{ close: []; remove: [] }>()

const html = computed(() => renderMarkdown(cleanRecipeMarkdown(props.markdown)))
const confirmingDelete = ref(false)

watch(() => [props.open, props.title], () => {
  confirmingDelete.value = false
})
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
      <footer class="recipe-modal-foot">
        <div class="recipe-modal-actions">
          <a v-if="sourceUrl" class="source-link" :href="sourceUrl" target="_blank" rel="noopener noreferrer">
            打开原始来源 <span aria-hidden="true">↗</span>
          </a>
          <button v-if="!confirmingDelete" type="button" class="danger recipe-delete-trigger"
                  aria-label="删除菜谱" title="删除菜谱" @click="confirmingDelete = true">删除</button>
        </div>
        <section v-if="confirmingDelete" class="recipe-delete-confirm" aria-label="确认删除菜谱">
          <div>
            <strong>确认删除「{{ title }}」？</strong>
            <p>原文和检索索引都会被删除，此操作无法撤销。</p>
          </div>
          <div class="recipe-delete-actions">
            <button type="button" class="secondary" :disabled="deleting" @click="confirmingDelete = false">取消</button>
            <button type="button" class="danger" data-action="confirm-delete" :disabled="deleting" @click="emit('remove')">
              {{ deleting ? '正在删除…' : '确认删除' }}
            </button>
          </div>
          <p v-if="deleteError" class="error recipe-delete-error">{{ deleteError }}</p>
        </section>
      </footer>
    </section>
    </div>
  </Teleport>
</template>

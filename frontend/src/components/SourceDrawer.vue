<script setup lang="ts">
defineProps<{ source: Record<string, unknown> | null }>()
defineEmits<{ close: [] }>()
const safeUrl = (value: unknown) => typeof value === 'string' && /^https?:\/\//i.test(value) ? value : undefined
</script>
<template><aside v-if="source" class="source-drawer" role="dialog" aria-label="回答来源"><button class="close" @click="$emit('close')">关闭</button><h2>{{ source.title || '来源快照' }}</h2><p v-if="source.source_available === false" class="warning">原文已删除或不可用，以下为回答时保存的证据。</p><p class="source-content">{{ source.content || '该历史引用未保存正文片段。' }}</p><a v-if="safeUrl(source.source_url)" :href="safeUrl(source.source_url)" target="_blank" rel="noopener noreferrer">查看原始来源</a><small v-if="source.content_hash">版本：{{ String(source.content_hash).slice(0,12) }}</small></aside></template>
<style scoped>.source-content{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7}small{display:block;margin-top:16px}</style>

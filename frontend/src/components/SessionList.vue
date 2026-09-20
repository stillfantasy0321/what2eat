<script setup lang="ts">
export interface SessionSummary { id: string; title: string; updated_at: string }
defineProps<{ sessions: SessionSummary[]; currentId: string }>()
const emit = defineEmits<{
  create: []
  choose: [id: string]
  remove: [id: string]
}>()
</script>
<template>
  <aside class="session-list" aria-label="对话列表">
    <button class="primary" type="button" @click="$emit('create')">新建对话</button>
    <article v-for="item in sessions" :key="item.id" :class="{ active: item.id === currentId }">
      <button class="session-title" type="button" @click="$emit('choose', item.id)">{{ item.title }}</button>
      <button type="button" class="session-delete" data-action="delete-session" :aria-label="`删除会话 ${item.title}`" @click="$emit('remove', item.id)">删除</button>
    </article>
  </aside>
</template>

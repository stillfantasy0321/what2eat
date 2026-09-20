<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { api } from '../api/client'
import { useChat } from '../composables/useChat'
import { renderMarkdown } from '../lib/markdown'
import QuickActions from './QuickActions.vue'

const props = defineProps<{ sessionId: string }>()
const emit = defineEmits<{ sourceOpen: [source: Record<string, unknown>] }>()
const text = ref(''), list = ref<HTMLElement | null>(null)
const categories = ref<string[]>([])
const { messages, status, error, start, stop, loadHistory, loadOlder, olderCursor } = useChat()
const showQuickActions = computed(() => !messages.value.some(message => message.role === 'user'))

watch(() => props.sessionId, id => {
  stop()
  if (id) loadHistory(id).catch(reason => {
    error.value = reason instanceof Error ? reason.message : '对话加载失败'
  })
}, { immediate: true })

watch(messages, async () => {
  if (!messages.value.length) return
  await nextTick()
  const element = list.value
  if (!element) return
  if (typeof element.scrollTo === 'function') element.scrollTo({ top: element.scrollHeight })
  else element.scrollTop = element.scrollHeight
}, { deep: true })

async function send() {
  const value = text.value.trim()
  if (!value || status.value === 'streaming') return
  text.value = ''
  await start(props.sessionId, value)
}

async function sendPrompt(prompt: string) {
  if (status.value !== 'streaming') await start(props.sessionId, prompt)
}

onMounted(async () => {
  try {
    categories.value = (await api<{ items: string[] }>('/api/recipes/categories')).items
  } catch {
    categories.value = []
  }
})
</script>

<template>
  <section class="chat-panel">
    <div ref="list" class="chat-log">
      <QuickActions v-if="showQuickActions" :busy="status === 'streaming'" :categories="categories" @send="sendPrompt" />
      <button v-if="olderCursor !== null" @click="loadOlder(sessionId)">加载更早的消息</button>
      <article v-for="message in messages" :key="message.id" :class="['bubble', message.role]">
        <div v-if="message.role === 'assistant'" class="bubble-markdown" v-html="renderMarkdown(message.content || '正在整理菜谱…')" />
        <p v-else class="bubble-text">{{ message.content }}</p>
        <small v-if="message.status !== 'complete'">{{ message.status }}</small>
        <button v-for="(source, index) in message.sources" :key="index" class="source-chip" @click="emit('sourceOpen', source)">来源 {{ index + 1 }}</button>
      </article>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <form @submit.prevent="send">
      <textarea v-model="text" rows="2" placeholder="问做法、换菜，或让我列购物清单" />
      <button :disabled="status === 'streaming'">{{ status === 'streaming' ? '正在回答…' : '发送' }}</button>
      <button v-if="status === 'streaming'" type="button" class="secondary" @click="stop">停止</button>
    </form>
  </section>
</template>
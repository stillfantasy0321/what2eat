import { onScopeDispose, reactive, ref } from 'vue'
import { api, ApiError } from '../api/client'
import { readSse } from '../api/sse'
import type { ChatMessage } from '../api/types'

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const status = ref<'idle' | 'streaming' | 'complete' | 'error'>('idle')
  const error = ref('')
  let controller: AbortController | null = null
  let pendingRequestId: string | null = null
  let activeSession = ''
  const olderCursor = ref<number | null>(null)

  async function loadHistory(sessionId: string) {
    if (activeSession !== sessionId) { stop(); activeSession = sessionId; messages.value = [] }
    const page = await api<{ items: ChatMessage[]; next_cursor: number | null }>(`/api/sessions/${sessionId}/messages?limit=100`)
    if (activeSession !== sessionId) return
    messages.value = page.items
    olderCursor.value = page.next_cursor
  }

  async function start(sessionId: string, text: string) {
    stop()
    const requestController = new AbortController()
    controller = requestController
    activeSession = sessionId
    pendingRequestId = crypto.randomUUID()
    const user: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text, status: 'complete' }
    const assistant = reactive<ChatMessage>({ id: pendingRequestId, role: 'assistant', content: '', status: 'streaming' })
    messages.value.push(user, assistant)
    status.value = 'streaming'
    error.value = ''
    try {
      const response = await fetch('/api/chat', {
        method: 'POST', signal: requestController.signal, headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, request_id: pendingRequestId, message: text }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { error?: { code?: string; message?: string } }
        throw new ApiError(response.status, body.error?.code ?? 'http_error', body.error?.message ?? '对话请求失败')
      }
      if (!response.body) throw new Error('浏览器未收到流式响应。')
      for await (const event of readSse(response.body)) {
        if (requestController.signal.aborted || controller !== requestController) return
        if (event.event === 'delta') assistant.content += String(event.data.text ?? '')
        if (event.event === 'reset') assistant.content = String(event.data.text ?? '')
        if (event.event === 'result') assistant.content = String(event.data.text ?? assistant.content)
        if (event.event === 'sources') assistant.sources = event.data.items as Record<string, unknown>[]
        if (event.event === 'error') throw new Error(String(event.data.message ?? '生成失败'))
        if (event.event === 'done') {
          assistant.status = 'complete'
          status.value = 'complete'
          pendingRequestId = null
        }
      }
      if (requestController.signal.aborted || controller !== requestController) return
      if (status.value !== 'complete') { status.value = 'error'; error.value = '连接已中断，已恢复保存的消息。'; await loadHistory(sessionId) }
    } catch (reason) {
      if (requestController.signal.aborted || controller !== requestController) return
      assistant.status = 'interrupted'
      status.value = 'error'
      error.value = reason instanceof Error ? reason.message : '对话中断'
      await loadHistory(sessionId).catch(() => undefined)
    }
  }

  function stop() {
    controller?.abort(); controller = null; pendingRequestId = null
    if (status.value === 'streaming') {
      const last = messages.value.at(-1); if (last?.status === 'streaming') last.status = 'cancelled'
      status.value = 'idle'
    }
  }
  async function loadOlder(sessionId: string) {
    if (olderCursor.value === null) return
    const page = await api<{items: ChatMessage[]; next_cursor: number | null}>(`/api/sessions/${sessionId}/messages?limit=100&before_seq=${olderCursor.value}`)
    if (activeSession !== sessionId) return
    messages.value.unshift(...page.items); olderCursor.value = page.next_cursor
  }
  function newAttempt() { pendingRequestId = null }
  onScopeDispose(stop)
  return { messages, status, error, start, stop, loadHistory, loadOlder, olderCursor, newAttempt }
}

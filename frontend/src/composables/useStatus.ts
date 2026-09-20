import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { ServiceStatus } from '../api/types'

export function useStatus() {
  const status = ref<ServiceStatus | null>(null)
  const error = ref('')
  const loading = ref(false)
  async function refresh() {
    loading.value = true
    error.value = ''
    try { status.value = await api<ServiceStatus>('/api/status') }
    catch (reason) { error.value = reason instanceof Error ? reason.message : '服务状态读取失败' }
    finally { loading.value = false }
  }
  onMounted(refresh)
  return { status, error, loading, refresh }
}

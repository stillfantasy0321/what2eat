import type { ApiFailure } from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) { super(message) }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData) && !headers.has('content-type')) {
    headers.set('content-type', 'application/json')
  }
  const response = await fetch(path, { ...init, headers })
  if (response.ok && response.status === 204) return undefined as T
  const contentType = response.headers.get('content-type') ?? ''
  const data = contentType.includes('application/json')
    ? await response.json() as T & ApiFailure
    : undefined
  if (!response.ok) {
    const detail = data?.error
    throw new ApiError(response.status, detail?.code ?? 'http_error',
      detail?.message ?? `请求失败（${response.status}）`, detail?.request_id)
  }
  if (data === undefined) throw new ApiError(response.status, 'invalid_response', '服务器返回了非 JSON 数据。')
  return data as T
}

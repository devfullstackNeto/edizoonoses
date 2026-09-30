import { describe, expect, it } from 'vitest'
import { api } from './api'

describe('API contract', () => {
  it('adds bearer authorization and returns JSON', async () => {
    const storage = new Map([['edi_token', 'demo-token']])
    Object.defineProperty(globalThis, 'sessionStorage', { value: { getItem: (k: string) => storage.get(k) } })
    globalThis.fetch = async (_url: RequestInfo | URL, options?: RequestInit) => {
      expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer demo-token')
      return new Response(JSON.stringify({ total: 50 }), { status: 200 })
    }
    expect((await api<{ total: number }>('/dashboard')).total).toBe(50)
  })
})

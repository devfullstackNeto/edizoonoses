export type User = { id: string; name: string; email: string; role: string }
export type Occurrence = { id: string; protocol: string; type: string; description: string; address: string; latitude: number | null; longitude: number | null; territory: string; status: string; priority: string; risk_score: number; occurred_at: string; assigned_to: string | null; source: string; notes: string; tags: string[]; timeline?: { action: string; payload: Record<string, unknown>; created_at: string }[] }
export type Document = { id: string; name: string; mime: string; size: number; sha256: string; classification: string; version: number; created_at: string; occurrence_id: string | null; parent_id: string | null; tags: string[] }
const base = '/api/v1'
export const token = () => sessionStorage.getItem('edi_token') || ''
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token()}`, ...((options.headers || {}) as Record<string, string>) }
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${base}${path}`, { ...options, headers })
  if (!res.ok) { let detail = `${res.status}`; try { const data = await res.json(); detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail) } catch { /* preserve status */ } throw new Error(detail) }
  return res.json() as Promise<T>
}
export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const patch = <T,>(path: string, body: unknown) => api<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
export async function previewBlob(path: string) {
  const res = await fetch(`${base}${path}`, { headers: { Authorization: `Bearer ${token()}` } })
  if (!res.ok) throw new Error(`Falha na prévia: ${res.status}`)
  return URL.createObjectURL(await res.blob())
}
export async function download(path: string, name: string) {
  const res = await fetch(`${base}${path}`, { headers: { Authorization: `Bearer ${token()}` } })
  if (!res.ok) throw new Error(`Falha ao baixar: ${res.status}`)
  const url = URL.createObjectURL(await res.blob()); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url)
}

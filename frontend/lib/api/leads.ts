import { authenticatedFetch } from '../authenticatedFetch'

export type LeadStatus = 'waitlist' | 'invited' | 'converted' | 'lost'

export type LeadListItemOut = {
  id: string
  email: string
  first_name?: string | null
  last_name?: string | null
  phone?: string | null
  status: LeadStatus
  tags: string[]
  created_at: string
}

export type LeadDetailOut = LeadListItemOut & {
  source?: string | null
  utm_source?: string | null
  utm_medium?: string | null
  utm_campaign?: string | null
  notes?: string | null
  last_contacted_at?: string | null
  consent_email: 'opted_in' | 'opted_out' | 'unknown'
  consent_sms: 'opted_in' | 'opted_out' | 'unknown'
}

export type LeadEventOut = {
  id: string
  channel: 'email' | 'sms'
  type: 'send' | 'open' | 'click' | 'bounce' | 'complaint'
  occurred_at: string
  meta: Record<string, any>
}

export type LeadListResponse = {
  items: LeadListItemOut[]
  total: number
  limit: number
  offset: number
}

export async function listLeads(params: { q?: string; status?: string; tag?: string; dateFrom?: string; dateTo?: string; limit?: number; offset?: number }): Promise<LeadListResponse> {
  const url = new URL('/leads', 'http://local')
  if (params.q) url.searchParams.set('q', params.q)
  if (params.status) url.searchParams.set('status', params.status)
  if (params.tag) url.searchParams.set('tag', params.tag)
  if (params.dateFrom) url.searchParams.set('date_from', params.dateFrom)
  if (params.dateTo) url.searchParams.set('date_to', params.dateTo)
  if (params.limit != null) url.searchParams.set('limit', String(params.limit))
  if (params.offset != null) url.searchParams.set('offset', String(params.offset))
  const res = await authenticatedFetch(url.pathname + '?' + url.searchParams.toString(), { method: 'GET' })
  if (!res.ok) throw new Error('Failed to list leads')
  return res.json()
}

export async function getLead(id: string): Promise<LeadDetailOut> {
  const res = await authenticatedFetch(`/leads/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error('Failed to get lead')
  return res.json()
}

export async function getLeadEvents(id: string): Promise<LeadEventOut[]> {
  const r = await fetch(`/api/leads/${encodeURIComponent(id)}/events`, { credentials: 'include' })
  if (r.ok) return r.json()
  return []
}

export async function updateLeadStatus(id: string, status: LeadStatus): Promise<void> {
  const res = await authenticatedFetch(`/leads/${encodeURIComponent(id)}/status`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ status })
  })
  if (!res.ok) throw new Error('Failed to update status')
}

export async function patchLeadFields(id: string, body: { tags?: string[]; phone?: string }): Promise<LeadDetailOut> {
  const res = await authenticatedFetch(`/leads/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!res.ok) throw new Error('Failed to patch lead')
  return res.json()
}

export async function patchLeadNotes(id: string, notes: string): Promise<void> {
  const res = await authenticatedFetch(`/leads/${encodeURIComponent(id)}/notes`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ notes })
  })
  if (!res.ok) throw new Error('Failed to patch notes')
}

export async function exportLeadsCSV(filters: { q?: string; status?: string; tag?: string; dateFrom?: string; dateTo?: string }) {
  const resp = await fetch(`/api/leads/export`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      q: filters.q || null,
      status: filters.status || null,
      date_from: filters.dateFrom || null,
      date_to: filters.dateTo || null,
      tag: filters.tag || null,
    }),
    credentials: 'include',
  })
  if (!resp.ok) throw new Error('Export failed')
  const blob = await resp.blob()
  const a = document.createElement('a')
  const urlObj = URL.createObjectURL(blob)
  a.href = urlObj
  const dateStr = new Date().toISOString().slice(0,10).replace(/-/g,'')
  a.download = `leads_export_${dateStr}.csv`
  a.click()
  URL.revokeObjectURL(urlObj)
}

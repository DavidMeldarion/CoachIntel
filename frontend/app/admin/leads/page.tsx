'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { authenticatedFetch } from '../../../lib/authenticatedFetch'

// Types matching backend responses
type LeadOut = {
  id: string
  email: string
  first_name?: string | null
  last_name?: string | null
  status: 'waitlist' | 'invited' | 'converted' | 'lost'
  tags?: string[] | null
  created_at?: string | null
}

type LeadsPageOut = {
  items: LeadOut[]
  total: number
  limit: number
  offset: number
}

const STATUSES = ['waitlist', 'invited', 'converted', 'lost'] as const

export default function AdminLeadsPage() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<string>('')
  const [page, setPage] = useState(0)
  const [limit, setLimit] = useState(25)
  const [data, setData] = useState<LeadsPageOut | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const offset = page * limit

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      if (status) params.set('status', status)
      params.set('limit', String(limit))
      params.set('offset', String(offset))
      const res = await fetch(`/api/leads?${params.toString()}`, { credentials: 'include' })
      if (!res.ok) throw new Error(`Failed to load leads (${res.status})`)
      const json = (await res.json()) as LeadsPageOut
      setData(json)
    } catch (e: any) {
      setError(e?.message || 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, status, limit, page])

  function exportCsv() {
    if (!data?.items?.length) return
    const headers = ['created_at', 'status', 'name', 'email', 'tags']
    const rows = data.items.map((l) => [
      l.created_at || '',
      l.status,
      `${(l.first_name||'').trim()} ${(l.last_name||'').trim()}`.trim(),
      l.email,
      (l.tags||[]).join(';')
    ])
    const csv = [headers, ...rows].map(r => r.map(x => `"${String(x).replace(/"/g,'""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `leads-${new Date().toISOString().slice(0,10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function updateStatus(id: string, next: LeadOut['status']) {
    // optimistic update
    setData((prev) => prev ? { ...prev, items: prev.items.map(i => i.id === id ? { ...i, status: next } : i) } : prev)
    const res = await authenticatedFetch(`/leads/${encodeURIComponent(id)}/status`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: next })
    })
    if (!res.ok) {
      // revert
      setData((prev) => prev ? { ...prev, items: prev.items.map(i => i.id === id ? { ...i, status: (data?.items.find(x=>x.id===id)?.status||'waitlist') } : i) } : prev)
      alert('Failed to update status')
    }
  }

  const [drawerId, setDrawerId] = useState<string | null>(null)
  const selected = useMemo(() => data?.items.find(i => i.id === drawerId) || null, [data, drawerId])

  return (
    <div className="p-6">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <input
            value={q}
            onChange={(e)=>{ setPage(0); setQ(e.target.value) }}
            placeholder="Search email or name..."
            className="border rounded px-3 py-2 w-64"
          />
          <select value={status} onChange={(e)=>{ setPage(0); setStatus(e.target.value) }} className="border rounded px-3 py-2">
            <option value="">All statuses</option>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <button onClick={exportCsv} className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-3 py-2 rounded border">Export CSV</button>
      </div>

      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_,i)=> (
            <div key={i} className="animate-pulse h-10 bg-gray-100 rounded" />
          ))}
        </div>
      )}

      {error && (
        <div className="text-red-600 text-sm mb-3">{error}</div>
      )}

      {!loading && data && data.items.length === 0 && (
        <div className="text-gray-500 text-sm">No leads found.</div>
      )}

      {!loading && data && data.items.length > 0 && (
        <div className="border rounded overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2">Created</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-left px-3 py-2">Name</th>
                <th className="text-left px-3 py-2">Email</th>
                <th className="text-left px-3 py-2">Tags</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((l) => (
                <tr key={l.id} className="border-t">
                  <td className="px-3 py-2 text-gray-600">{l.created_at ? new Date(l.created_at).toLocaleString() : ''}</td>
                  <td className="px-3 py-2">
                    <select value={l.status} onChange={(e)=>updateStatus(l.id, e.target.value as any)} className="border rounded px-2 py-1 text-xs">
                      {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2">{`${l.first_name||''} ${l.last_name||''}`.trim()}</td>
                  <td className="px-3 py-2">{l.email}</td>
                  <td className="px-3 py-2">{(l.tags||[]).join(', ')}</td>
                  <td className="px-3 py-2 text-right"><button onClick={()=>setDrawerId(l.id)} className="text-blue-600 hover:underline text-xs">Details</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {data && (
        <div className="flex items-center justify-between mt-3 text-sm">
          <div className="text-gray-500">Total: {data.total}</div>
          <div className="flex items-center gap-2">
            <button disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))} className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
            <span>Page {page+1}</span>
            <button disabled={offset + limit >= data.total} onClick={()=>setPage(p=>p+1)} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
          </div>
        </div>
      )}

      {/* Drawer */}
      {selected && (
        <LeadDrawer id={selected.id} onClose={()=>setDrawerId(null)} />
      )}
    </div>
  )
}

function LeadDrawer({ id, onClose }: { id: string; onClose: ()=>void }) {
  const [notes, setNotes] = useState('')
  const [events, setEvents] = useState<{ type: string; occurred_at: string }[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    ;(async ()=>{
      try {
        // fetch minimal lead details to get notes + events
        const res = await fetch(`/api/leads/${encodeURIComponent(id)}`)
        if (!res.ok) throw new Error()
        const json = await res.json()
        if (!mounted) return
        setNotes(json.notes || '')
        setEvents((json.events||[]).map((e:any)=>({ type: e.type, occurred_at: e.occurred_at })))
      } catch {
        // ignore
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [id])

  async function saveNotes() {
    // optimistic
    const prev = notes
    try {
      const res = await authenticatedFetch(`/leads/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ notes })
      })
      if (!res.ok) throw new Error()
    } catch {
      alert('Failed to save notes')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex justify-end">
      <div className="bg-white w-full max-w-md h-full shadow-xl p-4 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Lead Details</h3>
          <button onClick={onClose} className="text-sm text-gray-600 hover:text-gray-900">Close</button>
        </div>
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_,i)=> <div key={i} className="animate-pulse h-8 bg-gray-100 rounded" />)}
          </div>
        ) : (
          <div className="flex-1 overflow-auto">
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea className="w-full border rounded p-2 h-40" value={notes} onChange={(e)=>setNotes(e.target.value)} />
            <div className="mt-2 flex justify-end"><button onClick={saveNotes} className="px-3 py-1 border rounded">Save</button></div>

            <div className="mt-6">
              <div className="text-sm font-medium mb-2">Timeline</div>
              <div className="space-y-2">
                {events.length === 0 && <div className="text-sm text-gray-500">No events yet.</div>}
                {events.map((e, idx) => (
                  <div key={idx} className="text-sm text-gray-700 flex items-center justify-between">
                    <span className="capitalize">{e.type}</span>
                    <span className="text-gray-500">{new Date(e.occurred_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

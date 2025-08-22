'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import useSWR from 'swr'
import { listLeads, LeadListResponse, LeadStatus, updateLeadStatus, patchLeadFields, exportLeadsCSV } from '../../../lib/api/leads'
import { StatusPill } from '../../../components/StatusPill'
import { TagInput } from '../../../components/TagInput'
import LeadDrawer from './LeadDrawer'
import Link from 'next/link'
import { useSession } from 'next-auth/react'

function useQuerySync() {
  const search = useSearchParams()
  const router = useRouter()
  const set = (patch: Record<string,string|undefined>) => {
    const params = new URLSearchParams(search.toString())
    Object.entries(patch).forEach(([k,v])=>{
      if (v === undefined || v === '') params.delete(k)
      else params.set(k, v)
    })
    router.replace(`?${params.toString()}`)
  }
  return { search, set }
}

export default function AdminLeadsPage() {
  const { data: session, status } = useSession();
  const { search, set } = useQuerySync()
  const q = search.get('q') || ''
  const statusFilter = search.get('status') || ''
  const tag = search.get('tag') || ''
  const date_from = search.get('date_from') || ''
  const date_to = search.get('date_to') || ''
  const limit = Number(search.get('limit') || '50')
  const offset = Number(search.get('offset') || '0')

  const { data, isLoading, mutate } = useSWR<LeadListResponse>(['leads', q, statusFilter, tag, date_from, date_to, limit, offset],
    () => listLeads({ q, status: statusFilter || undefined, tag: tag || undefined, dateFrom: date_from || undefined, dateTo: date_to || undefined, limit, offset }),
    { keepPreviousData: true }
  )

  function onStatusChange(id: string, next: LeadStatus) {
    // optimistic
    mutate(async (prev)=>{
      const updated = prev ? { ...prev, items: prev.items.map(i => i.id === id ? { ...i, status: next } : i) } : prev
      try { await updateLeadStatus(id, next) } catch { return prev }
      return updated!
    }, { revalidate: true })
  }

  function onTagsChange(id: string, tags: string[]) {
    // debounce per-row
    debounced.current[id]?.()
    const fn = async () => {
      try {
        await patchLeadFields(id, { tags })
        mutate()
      } catch { /* ignore */ }
    }
    debounced.current[id] = debounce(fn, 600)
  }

  const debounced = useRef<Record<string, ()=>void>>({})

  async function inviteLead(email: string, id: string) {
    try {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE;
  const resp = await fetch(`${apiBase}/invites`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email }),
      })
      if (!resp.ok) throw new Error('Failed to create invite');
      const data = await resp.json();
      const url = data?.invite_url as string | undefined;
      if (url) {
        try { await navigator.clipboard.writeText(url) } catch {}
        // Optimistically mark invited
        await updateLeadStatus(id, 'invited')
        mutate(prev=> prev ? { ...prev, items: prev.items.map(i => i.id === id ? { ...i, status: 'invited' } : i) } : prev, false)
        alert('Invite link copied to clipboard');
      } else {
        alert('Invite created but missing URL');
      }
    } catch (e: any) {
      alert(e?.message || 'Failed to create invite');
    }
  }

  // Guard: Only site admins may view this page
  if (status === 'loading') {
    return <div className="p-6 text-gray-600">Loading…</div>
  }
  if (!(session as any)?.siteAdmin) {
    return (
      <div className="p-6">
        <div className="max-w-xl mx-auto bg-white border rounded p-6 text-center">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Access restricted</h2>
          <p className="text-gray-600 mb-4">This page is for site administrators to manage public leads.</p>
          <Link href="/dashboard" className="text-blue-600 hover:underline">Go to your dashboard</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="px-6">
      {/* Admin tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex gap-6" aria-label="Tabs">
          <Link href="/admin/leads" className="border-b-2 border-blue-600 px-1 pb-2 text-sm font-medium text-blue-600">Leads</Link>
          <Link href="/admin/org-admins" className="border-b-2 border-transparent px-1 pb-2 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">Org Admins</Link>
        </nav>
      </div>

      <div className="flex flex-wrap items-end gap-2 mb-4">
        <div className="flex flex-col">
          <label className="text-xs text-gray-600">Search</label>
          <input className="border rounded px-3 py-2 w-64" value={q} onChange={(e)=>set({ q: e.target.value, offset: '0' })} placeholder="Search name or email" />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-600">Status</label>
          <select className="border rounded px-3 py-2" value={statusFilter} onChange={(e)=>set({ status: e.target.value || undefined, offset: '0' })}>
            <option value="">All</option>
            <option value="waitlist">waitlist</option>
            <option value="invited">invited</option>
            <option value="converted">converted</option>
            <option value="lost">lost</option>
          </select>
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-600">Tag</label>
          <input className="border rounded px-3 py-2 w-48" value={tag} onChange={(e)=>set({ tag: e.target.value || undefined, offset: '0' })} placeholder="Tag" />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-600">From</label>
          <input type="date" className="border rounded px-3 py-2" value={date_from} onChange={(e)=>set({ date_from: e.target.value || undefined, offset: '0' })} />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-600">To</label>
          <input type="date" className="border rounded px-3 py-2" value={date_to} onChange={(e)=>set({ date_to: e.target.value || undefined, offset: '0' })} />
        </div>
        <div className="flex-1" />
        <button onClick={()=>exportLeadsCSV({ q, status, tag, dateFrom: date_from, dateTo: date_to })} className="border rounded px-3 py-2 bg-gray-50 hover:bg-gray-100">Export CSV</button>
      </div>

      <div className="border rounded overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-3 py-2">Created</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Email</th>
              <th className="text-left px-3 py-2">Phone</th>
              <th className="text-left px-3 py-2">Tags</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && Array.from({ length: 10 }).map((_,i)=> (
              <tr key={i} className="border-t">
                <td className="px-3 py-2"><div className="h-4 w-24 bg-gray-100 animate-pulse rounded" /></td>
                <td className="px-3 py-2"><div className="h-5 w-20 bg-gray-100 animate-pulse rounded-full" /></td>
                <td className="px-3 py-2"><div className="h-4 w-40 bg-gray-100 animate-pulse rounded" /></td>
                <td className="px-3 py-2"><div className="h-4 w-56 bg-gray-100 animate-pulse rounded" /></td>
                <td className="px-3 py-2"><div className="h-4 w-24 bg-gray-100 animate-pulse rounded" /></td>
                <td className="px-3 py-2"><div className="h-6 w-48 bg-gray-100 animate-pulse rounded" /></td>
                <td className="px-3 py-2"></td>
              </tr>
            ))}
            {!isLoading && data?.items?.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-500">No results. Clear filters to see all leads.</td></tr>
            )}
            {!isLoading && data?.items?.map((l)=> (
              <tr key={l.id} className="border-t hover:bg-gray-50">
                <td className="px-3 py-2 text-gray-600">{l.created_at ? new Date(l.created_at).toLocaleString() : ''}</td>
                <td className="px-3 py-2"><StatusPill id={l.id} status={l.status} onChange={(s)=>onStatusChange(l.id, s)} /></td>
                <td className="px-3 py-2">{`${l.first_name||''} ${l.last_name||''}`.trim()}</td>
                <td className="px-3 py-2">{l.email}</td>
                <td className="px-3 py-2">{l.phone || ''}</td>
                <td className="px-3 py-2">
                  <TagInput value={l.tags||[]} onChange={(tags)=>{ onTagsChange(l.id, tags); mutate(prev=> prev ? { ...prev, items: prev.items.map(i=> i.id===l.id ? { ...i, tags } : i) } : prev, false) }} />
                </td>
                <td className="px-3 py-2 text-right flex items-center gap-3 justify-end">
                  <button onClick={()=>inviteLead(l.email, l.id)} className="text-gray-700 hover:underline text-xs">Invite</button>
                  <LeadDrawerTrigger id={l.id} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-3 text-sm">
        <div className="text-gray-600">Total: {data?.total ?? 0}</div>
        <div className="flex items-center gap-2">
          <button disabled={offset===0} onClick={()=>set({ offset: String(Math.max(0, offset - limit)) })} className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
          <span>{offset/limit + 1}</span>
          <button disabled={!!data && offset + limit >= (data?.total||0)} onClick={()=>set({ offset: String(offset + limit) })} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
          <select value={String(limit)} onChange={(e)=>set({ limit: e.target.value, offset: '0' })} className="border rounded px-2 py-1">
            {[25,50,100,150,200].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>
    </div>
  )
}

function debounce(fn: ()=>void, ms: number) {
  let t: any
  return () => { clearTimeout(t); t = setTimeout(fn, ms) }
}

function LeadDrawerTrigger({ id }: { id: string }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button onClick={()=>setOpen(true)} className="text-blue-600 hover:underline text-xs">Details</button>
      {open && <LeadDrawer id={id} onClose={()=>setOpen(false)} />}
    </>
  )
}

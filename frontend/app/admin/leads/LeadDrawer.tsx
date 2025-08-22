'use client'
import { useEffect, useRef, useState } from 'react'
import { LeadDetailOut, LeadEventOut, patchLeadFields, patchLeadNotes, updateLeadStatus } from '../../../lib/api/leads'
import { StatusPill } from '../../../components/StatusPill'

export default function LeadDrawer({ id, onClose }: { id: string; onClose: ()=>void }) {
  const [detail, setDetail] = useState<LeadDetailOut | null>(null)
  const [events, setEvents] = useState<LeadEventOut[]>([])
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(()=>{
    let mounted = true
    ;(async()=>{
      const apiBase = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${apiBase}/leads/${encodeURIComponent(id)}`, { credentials: 'include' })
      if (res.ok) {
        const d: LeadDetailOut = await res.json()
        if (!mounted) return
        setDetail(d)
        setNotes(d.notes || '')
      }
      const e = await fetch(`${apiBase}/leads/${encodeURIComponent(id)}/events`, { credentials: 'include' })
      if (e.ok) setEvents(await e.json())
    })()
    return ()=>{ mounted = false }
  }, [id])

  async function savePhone(next: string) {
    setSaving(true)
    try {
      const d = await patchLeadFields(id, { phone: next })
      setDetail(d)
    } finally { setSaving(false) }
  }

  const timer = useRef<any>(null)
  function debounceNotes(next: string) {
    setNotes(next)
    clearTimeout(timer.current)
    timer.current = setTimeout(async ()=>{
      await patchLeadNotes(id, next)
    }, 800)
  }

  async function setStatus(next: any) {
    await updateLeadStatus(id, next)
    setDetail((d)=> d ? { ...d, status: next } : d)
  }

  async function generateInviteAndCopy() {
    if (!detail?.email) return;
    try {
  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  const resp = await fetch(`${apiBase}/invites`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: detail.email }),
      })
      if (!resp.ok) throw new Error('Failed to create invite');
      const data = await resp.json();
      const url = data?.invite_url as string | undefined;
      if (url) {
        await navigator.clipboard.writeText(url);
        // Optimistically mark invited
        await setStatus('invited');
        alert('Invite link copied to clipboard');
      } else {
        alert('Invite created but missing URL');
      }
    } catch (e: any) {
      alert(e?.message || 'Failed to create invite');
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex justify-end">
      <div className="bg-white w-full max-w-lg h-full shadow-xl p-4 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-lg font-semibold">{detail ? `${detail.first_name||''} ${detail.last_name||''}`.trim() : 'Lead'}</div>
            <div className="text-xs text-gray-500">{detail?.created_at ? new Date(detail.created_at).toLocaleString() : ''}</div>
          </div>
          <button onClick={onClose} className="text-sm text-gray-600 hover:text-gray-900">Close</button>
        </div>
        {detail ? (
          <div className="flex-1 overflow-auto">
            <div className="flex items-center gap-2 mb-4"><StatusPill id={id} status={detail.status} onChange={setStatus} /></div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-gray-500">Email</div>
                <div>{detail.email}</div>
              </div>
              <div>
                <div className="text-gray-500">Phone</div>
                <input defaultValue={detail.phone || ''} onBlur={(e)=>savePhone(e.target.value)} className="border rounded px-2 py-1 w-full" />
              </div>
              <div>
                <div className="text-gray-500">Source</div>
                <div>{detail.source || '-'}</div>
              </div>
              <div>
                <div className="text-gray-500">UTM Source</div>
                <div>{detail.utm_source || '-'}</div>
              </div>
              <div>
                <div className="text-gray-500">UTM Medium</div>
                <div>{detail.utm_medium || '-'}</div>
              </div>
              <div>
                <div className="text-gray-500">UTM Campaign</div>
                <div>{detail.utm_campaign || '-'}</div>
              </div>
              <div>
                <div className="text-gray-500">Consent (Email)</div>
                <div className="capitalize">{detail.consent_email}</div>
              </div>
              <div>
                <div className="text-gray-500">Consent (SMS)</div>
                <div className="capitalize">{detail.consent_sms}</div>
              </div>
            </div>

            <div className="mt-6">
              <div className="font-medium mb-1">Notes</div>
              <textarea className="w-full border rounded p-2 h-32" value={notes} onChange={(e)=>debounceNotes(e.target.value)} />
            </div>

            <div className="mt-6">
              <div className="font-medium mb-2">Activity</div>
              <div className="space-y-2">
                {events.length === 0 && <div className="text-sm text-gray-500">No events</div>}
                {events.map(ev => (
                  <div key={ev.id} className="text-sm flex items-center justify-between">
                    <span className="capitalize">{ev.type}</span>
                    <span className="text-gray-500">{new Date(ev.occurred_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1" />
        )}

        <div className="border-t pt-3 mt-3 flex items-center justify-between">
          <div className="text-xs text-gray-500">Last contacted: {detail?.last_contacted_at ? new Date(detail.last_contacted_at).toLocaleString() : '-'}</div>
          <div className="flex gap-2">
            <button onClick={generateInviteAndCopy} className="px-3 py-1 border rounded">Invite (copy link)</button>
            <button onClick={()=>setStatus('converted')} className="px-3 py-1 border rounded">Convert</button>
            <button onClick={()=>setStatus('lost')} className="px-3 py-1 border rounded">Mark Lost</button>
          </div>
        </div>
      </div>
    </div>
  )
}

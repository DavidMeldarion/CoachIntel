"use client"
import { useState } from 'react'
import { LeadStatus, updateLeadStatus } from '../lib/api/leads'

const COLORS: Record<LeadStatus, string> = {
  waitlist: 'bg-gray-100 text-gray-800 border-gray-300',
  invited: 'bg-blue-100 text-blue-800 border-blue-300',
  converted: 'bg-green-100 text-green-800 border-green-300',
  lost: 'bg-red-100 text-red-800 border-red-300',
}

export function StatusPill({ id, status, onChange }: { id: string; status: LeadStatus; onChange?: (s: LeadStatus)=>void }) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [value, setValue] = useState<LeadStatus>(status)

  async function change(next: LeadStatus) {
    if (next === value) return
    setPending(true)
    const prev = value
    setValue(next)
    onChange?.(next)
    try {
      await updateLeadStatus(id, next)
    } catch {
      setValue(prev)
      onChange?.(prev)
      alert('Failed to update status')
    } finally {
      setPending(false)
      setOpen(false)
    }
  }

  const opts: LeadStatus[] = ['waitlist','invited','converted','lost']

  return (
    <div className="relative inline-block text-xs">
      <button onClick={()=>setOpen(o=>!o)} disabled={pending} className={`px-2 py-1 border rounded-full ${COLORS[value]} ${pending?'opacity-50':''}`}>
        {value}
      </button>
      {open && (
        <div className="absolute z-10 mt-1 bg-white border rounded shadow w-32">
          {opts.map(o => (
            <button key={o} onClick={()=>change(o)} className="block w-full text-left px-3 py-1.5 hover:bg-gray-50 text-gray-800">
              {o}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

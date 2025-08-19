"use client"
import { useEffect, useState } from 'react'

export function TagInput({ value, onChange, max = 10 }: { value: string[]; onChange: (tags: string[])=>void; max?: number }) {
  const [input, setInput] = useState('')
  const [tags, setTags] = useState<string[]>(value || [])

  useEffect(()=>{ setTags(value || []) }, [value])

  function addTag(raw: string) {
    const t = raw.trim()
    if (!t) return
    if (tags.includes(t)) return
    if (tags.length >= max) return
    const next = [...tags, t]
    setTags(next)
    onChange(next)
    setInput('')
  }

  function removeTag(t: string) {
    const next = tags.filter(x => x !== t)
    setTags(next)
    onChange(next)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTag(input)
    } else if (e.key === 'Backspace' && !input && tags.length) {
      removeTag(tags[tags.length-1])
    }
  }

  return (
    <div className="border rounded px-2 py-1 flex flex-wrap gap-1">
      {tags.map(t => (
        <span key={t} className="inline-flex items-center gap-1 bg-gray-100 text-gray-800 border border-gray-300 rounded-full px-2 py-0.5 text-xs">
          {t}
          <button className="text-gray-500 hover:text-gray-800" onClick={()=>removeTag(t)}>×</button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e)=>setInput(e.target.value)}
        onKeyDown={onKeyDown}
        className="flex-1 min-w-[120px] outline-none"
        placeholder="Add tag"
      />
    </div>
  )
}

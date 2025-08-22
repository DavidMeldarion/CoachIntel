import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

// Proxy a lead fetch (placeholder: consider calling your backend origin directly instead of another Next route)
export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
  try {
    const res = await fetch(`/api/leads/${encodeURIComponent(params.id)}`, {
      cache: 'no-store',
      headers: { cookie: request.headers.get('cookie') || '' },
    })
  const body = await res.text()
  return new NextResponse(body, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (err) {
  return NextResponse.json({ error: 'Not implemented' }, { status: 404 })
  }
}

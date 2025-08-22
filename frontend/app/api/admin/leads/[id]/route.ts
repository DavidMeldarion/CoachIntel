import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

// Proxy a lead fetch (placeholder: consider calling backend origin directly instead of chaining through /api/leads)
export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params
    const res = await fetch(`/api/leads/${encodeURIComponent(id)}`, {
      cache: 'no-store',
      headers: { cookie: request.headers.get('cookie') || '' },
    })
    const body = await res.text()
    return new NextResponse(body, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (err) {
    return NextResponse.json({ error: 'Not implemented' }, { status: 404 })
  }
}

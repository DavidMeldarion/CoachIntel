export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '../../../../lib/serverFetch'

// Previously proxied via /api/leads (internal hop). Now calls backend directly.
export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const search = url.search || ''
  const resp = await backendFetch(`/leads${search}`)
  const body = await resp.text()
  return new NextResponse(body, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } })
}

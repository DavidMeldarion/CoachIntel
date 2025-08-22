import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { backendFetch } from '../../../../../lib/serverFetch'

// Local RouteContext alias (dynamic params Promise pattern)
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
type RouteContext<TPath extends string> = { params: Promise<Record<string,string>> }

export const dynamic = 'force-dynamic';

export async function GET(
 _req: NextRequest,
 ctx: RouteContext<'/api/admin/leads/[id]'>
) {
  try {
    const { id } = await ctx.params
    const res = await backendFetch(`/leads/${encodeURIComponent(id)}`)
    const body = await res.text()
    return new NextResponse(body, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (err) {
    return NextResponse.json({ error: 'Not implemented' }, { status: 404 })
  }
}

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { getServerApiBase } from '../../../../../lib/serverApi'
import { getToken } from 'next-auth/jwt'

// Local fallback RouteContext generic (see comment in sibling route file)
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
type RouteContext<TPath extends string> = { params: Promise<Record<string,string>> }

export async function GET(request: NextRequest, ctx: RouteContext<'/api/leads/[id]/events'>) {
  const API_BASE = getServerApiBase()
  const { id } = await ctx.params
  const backendUrl = `${API_BASE}/leads/${encodeURIComponent(id)}/events`
  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET })
  const headers: Record<string,string> = {}
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string
  const resp = await fetch(backendUrl, { headers })
  const body = await resp.text()
  return new NextResponse(body, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } })
}

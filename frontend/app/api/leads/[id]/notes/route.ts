import { NextRequest, NextResponse } from 'next/server'
import { getServerApiBase } from '../../../../../lib/serverApi'
import { getToken } from 'next-auth/jwt'

// Local RouteContext helper (duplicated across route files; consider centralizing later)
type RouteContext<TPath extends string> = { params: Promise<Record<string, string>> }

export async function PATCH(request: NextRequest, ctx: RouteContext<'/api/leads/[id]/notes'>) {
  const { id } = await ctx.params
  const API_BASE = getServerApiBase()

  const backendUrl = `${API_BASE}/leads/${encodeURIComponent(id)}/notes`
  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET })
  const headers: Record<string,string> = { 'content-type': 'application/json' }
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string
  const body = await request.text()
  const resp = await fetch(backendUrl, { method: 'PATCH', headers, body })
  const text = await resp.text()
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } })
}

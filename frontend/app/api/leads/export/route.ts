import { NextRequest, NextResponse } from 'next/server'
import { getServerApiBase } from '../../../../lib/serverApi'
import { getToken } from 'next-auth/jwt'

export async function POST(request: NextRequest) {
  const API_BASE = getServerApiBase()
  const backendUrl = `${API_BASE}/leads/export`
  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET })
  const headers: Record<string,string> = { 'content-type': 'application/json' }
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string
  const cookie = (request as any).headers?.get?.('cookie') ?? undefined
  if (cookie) headers['cookie'] = cookie as string
  const body = await request.text()
  const resp = await fetch(backendUrl, { method: 'POST', headers, body, credentials: 'include' })
  const blob = await resp.arrayBuffer()
  return new NextResponse(blob, { status: resp.status, headers: { 'content-type': 'text/csv', 'content-disposition': resp.headers.get('content-disposition') || '' } })
}

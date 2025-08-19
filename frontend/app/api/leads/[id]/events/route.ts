import { NextRequest, NextResponse } from 'next/server'
import { getServerApiBase } from '../../../../../lib/serverApi'
import { getToken } from 'next-auth/jwt'

export async function GET(request: NextRequest, context: any) {
  const API_BASE = getServerApiBase()
  const id = context?.params?.id as string
  const backendUrl = `${API_BASE}/leads/${encodeURIComponent(id)}/events`
  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET })
  const headers: Record<string,string> = {}
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string
  const resp = await fetch(backendUrl, { headers })
  const body = await resp.text()
  return new NextResponse(body, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } })
}

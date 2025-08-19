import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../../../lib/serverApi';
import { getToken } from 'next-auth/jwt';

export async function POST(request: NextRequest, context: any) {
  const API_BASE = getServerApiBase();
  const id = context?.params?.id as string;
  const backendUrl = `${API_BASE}/leads/${encodeURIComponent(id)}/status`;

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;

  const body = await request.text();
  const resp = await fetch(backendUrl, { method: 'POST', headers, body });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

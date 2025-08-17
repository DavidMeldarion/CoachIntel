import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../lib/serverApi';
import { getToken } from 'next-auth/jwt';

export async function GET(request: NextRequest) {
  const API_BASE = getServerApiBase();
  const url = new URL(request.url);
  const q = url.searchParams.get('q');
  const status = url.searchParams.get('status');
  const limit = url.searchParams.get('limit');
  const offset = url.searchParams.get('offset');

  const backend = new URL(`${API_BASE}/leads`);
  if (q) backend.searchParams.set('q', q);
  if (status) backend.searchParams.set('status', status);
  if (limit) backend.searchParams.set('limit', limit);
  if (offset) backend.searchParams.set('offset', offset);

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = {};
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;

  const resp = await fetch(backend.toString(), {
    headers,
    credentials: 'include',
  });
  const body = await resp.text();
  return new NextResponse(body, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

export async function POST(request: NextRequest) {
  const API_BASE = getServerApiBase();
  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const isAuthed = Boolean((token as any)?.email);

  // Choose backend endpoint: authenticated org-scoped vs public CRM
  const backendUrl = isAuthed ? `${API_BASE}/leads` : `${API_BASE}/crm/public/leads`;

  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (isAuthed) headers['x-user-email'] = (token as any).email as string;

  const body = await request.text();
  const resp = await fetch(backendUrl, { method: 'POST', headers, body });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

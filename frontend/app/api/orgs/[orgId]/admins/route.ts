import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../../../lib/serverApi';
import { getToken } from 'next-auth/jwt';

export async function GET(request: NextRequest, { params }: { params: { orgId: string } }) {
  const API_BASE = getServerApiBase();
  const backendUrl = `${API_BASE}/orgs/${encodeURIComponent(params.orgId)}/admins`;

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = {};
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;
  const resp = await fetch(backendUrl, { headers, credentials: 'include' });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

export async function POST(request: NextRequest, { params }: { params: { orgId: string } }) {
  const API_BASE = getServerApiBase();
  const backendUrl = `${API_BASE}/orgs/${encodeURIComponent(params.orgId)}/admins`;

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;

  const body = await request.text();
  const resp = await fetch(backendUrl, { method: 'POST', headers, body, credentials: 'include' });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

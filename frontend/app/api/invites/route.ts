import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../lib/serverApi';
import { getToken } from 'next-auth/jwt';

// Create invite (admin only)
export async function POST(request: NextRequest) {
  const API_BASE = getServerApiBase();
  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;
  const body = await request.text();
  const resp = await fetch(`${API_BASE}/invites`, { method: 'POST', headers, body });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

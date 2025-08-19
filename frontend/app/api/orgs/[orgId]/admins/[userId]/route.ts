import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../../../../lib/serverApi';
import { getToken } from 'next-auth/jwt';

export async function DELETE(request: NextRequest, { params }: { params: { orgId: string, userId: string } }) {
  const API_BASE = getServerApiBase();
  const backendUrl = `${API_BASE}/orgs/${encodeURIComponent(params.orgId)}/admins/${encodeURIComponent(params.userId)}`;

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = {};
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;
  const resp = await fetch(backendUrl, { method: 'DELETE', headers, credentials: 'include' });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

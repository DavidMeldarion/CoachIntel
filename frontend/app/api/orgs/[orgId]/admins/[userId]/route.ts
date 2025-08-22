import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../../../../lib/serverApi';
import { getToken } from 'next-auth/jwt';

// Local RouteContext alias
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
type RouteContext<TPath extends string> = { params: Promise<Record<string,string>> }

export async function DELETE(request: NextRequest, ctx: RouteContext<'/api/orgs/[orgId]/admins/[userId]'>) {
  const { orgId, userId } = await ctx.params as any;
  const API_BASE = getServerApiBase();
  const backendUrl = `${API_BASE}/orgs/${encodeURIComponent(orgId)}/admins/${encodeURIComponent(userId)}`;

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = {};
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;
  const cookie = request.headers.get('cookie');
  if (cookie) headers['cookie'] = cookie;
  const auth = request.headers.get('authorization');
  if (auth) headers['authorization'] = auth;

  const resp = await fetch(backendUrl, { method: 'DELETE', headers });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

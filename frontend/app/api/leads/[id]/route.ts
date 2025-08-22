import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server'
import { getServerApiBase } from '../../../../lib/serverApi';
import { getToken } from 'next-auth/jwt';

// Local fallback type for RouteContext until provided by Next.js type generation
// Matches Next 15 internal: params is a Promise resolving to the dynamic segment map
// Adjust if upstream types change.
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
type RouteContext<TPath extends string> = { params: Promise<Record<string,string>> }

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  ctx: RouteContext<'/api/leads/[id]'>
) {
  const API_BASE = getServerApiBase();
  const { id } = await ctx.params
  const backendUrl = `${API_BASE}/leads/${encodeURIComponent(id)}`;

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = {};
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;
  const cookie = (request as any).headers?.get?.('cookie') ?? undefined;
  if (cookie) headers['cookie'] = cookie as string;

  const resp = await fetch(backendUrl, { headers, credentials: 'include' });
  const body = await resp.text();
  return new NextResponse(body, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

export async function PATCH(request: NextRequest, ctx: RouteContext<'/api/leads/[id]'>) {
  const API_BASE = getServerApiBase();
  const { id } = await ctx.params;
  const backendUrl = `${API_BASE}/leads/${encodeURIComponent(id)}`;

  const token = await getToken({ req: request as any, secret: process.env.NEXTAUTH_SECRET });
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if ((token as any)?.email) headers['x-user-email'] = (token as any).email as string;
  const cookie = (request as any).headers?.get?.('cookie') ?? undefined;
  if (cookie) headers['cookie'] = cookie as string;

  const body = await request.text();
  const resp = await fetch(backendUrl, { method: 'PATCH', headers, body, credentials: 'include' });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

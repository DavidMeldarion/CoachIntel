import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '../../../../lib/auth';

// Debug proxy: /api/clients/debug -> backend /clients/_debug
// NOTE: We intentionally avoid a folder named _debug because leading underscores
// are treated as "private" by Next.js App Router and excluded from the URL path.
const RAW_BACKEND_BASE = (process.env.NEXT_PUBLIC_BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://coachintel-backend:8000');
const BACKEND_BASE = RAW_BACKEND_BASE.replace(/\/$/, '');
const SERVICE_FALLBACK = 'http://coachintel-backend:8000';

function buildUrl(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  return `${BACKEND_BASE}/clients/_debug${qs ? `?${qs}` : ''}`;
}

async function forward(req: NextRequest) {
  // Try to obtain server session for automatic auth header injection
  let sessionEmail: string | null = null;
  try {
    const session = await getServerSession(authOptions);
    sessionEmail = session?.user?.email || null;
  } catch (e) {
    // ignore
  }
  const target = buildUrl(req);
  const headers: Record<string,string> = {};
  req.headers.forEach((v,k)=>{
    const low = k.toLowerCase();
    if (['host','connection','content-length'].includes(low)) return;
    headers[k] = v;
  });
  headers['x-forwarded-host'] = req.headers.get('host') || '';
  headers['x-forwarded-proto'] = req.nextUrl.protocol.replace(':','');
  if (sessionEmail && !headers['x-user-email']) {
    headers['x-user-email'] = sessionEmail;
  }
  if (sessionEmail && !headers['authorization']) {
    headers['authorization'] = `Bearer ${sessionEmail}`;
  }
  const start = Date.now();
  // eslint-disable-next-line no-console
  console.log('[ClientsDebugProxy] start', { target, BACKEND_BASE, injectedEmail: sessionEmail, finalUserEmail: headers['x-user-email'], hasAuthHeader: !!headers['authorization'] });
  let primaryError: any | null = null;
  try {
    const resp = await fetch(target, { method: 'GET', headers, redirect: 'manual' });
    // eslint-disable-next-line no-console
    console.log('[ClientsDebugProxy] primary_resp', { status: resp.status, elapsedMs: Date.now() - start });
    const outHeaders = new Headers();
    resp.headers.forEach((v,k)=>{
      if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
      outHeaders.set(k,v);
    });
    outHeaders.set('x-proxy-target', target);
    return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
  } catch (e:any) {
    primaryError = e;
    // eslint-disable-next-line no-console
    console.log('[ClientsDebugProxy] primary_error', { message: e?.message, elapsedMs: Date.now() - start });
  }
  const isLocalHost = /localhost|127\.0\.0\.1/.test(BACKEND_BASE);
  if (isLocalHost && BACKEND_BASE !== SERVICE_FALLBACK) {
    const fallbackTarget = target.replace(BACKEND_BASE, SERVICE_FALLBACK);
    try {
      // eslint-disable-next-line no-console
      console.log('[ClientsDebugProxy] fallback_attempt', { fallbackTarget });
      const resp = await fetch(fallbackTarget, { method: 'GET', headers, redirect: 'manual' });
      // eslint-disable-next-line no-console
      console.log('[ClientsDebugProxy] fallback_resp', { status: resp.status, elapsedMs: Date.now() - start });
      const outHeaders = new Headers();
      resp.headers.forEach((v,k)=>{
        if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
        outHeaders.set(k,v);
      });
      outHeaders.set('x-proxy-target', fallbackTarget);
      outHeaders.set('x-proxy-fallback', '1');
      return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
    } catch (e2:any) {
      // eslint-disable-next-line no-console
      console.log('[ClientsDebugProxy] fallback_error', { message: e2?.message, elapsedMs: Date.now() - start });
      return NextResponse.json({ error: 'Backend fetch failed (primary & fallback)', detail: e2?.message, target, fallbackTried: fallbackTarget, primaryError: primaryError?.message }, { status: 502 });
    }
  }
  return NextResponse.json({ error: 'Backend fetch failed', detail: primaryError?.message, target }, { status: 502 });
}

export async function GET(req: NextRequest) { return forward(req); }
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

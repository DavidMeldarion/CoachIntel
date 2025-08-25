import { NextRequest, NextResponse } from 'next/server';

// Direct clients proxy bypassing catch-all to avoid path issues
const RAW_BACKEND_BASE = (process.env.NEXT_PUBLIC_BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://coachintel-backend:8000');
const BACKEND_BASE = RAW_BACKEND_BASE.replace(/\/$/, '');
const SERVICE_FALLBACK = 'http://coachintel-backend:8000';

function buildUrl(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  return `${BACKEND_BASE}/clients${qs ? `?${qs}` : ''}`;
}

async function forward(method: string, req: NextRequest) {
  const target = buildUrl(req);
  const headers: Record<string,string> = {};
  req.headers.forEach((v,k)=>{
    const low = k.toLowerCase();
    if (['host','connection','content-length'].includes(low)) return;
    headers[k] = v;
  });
  headers['x-forwarded-host'] = req.headers.get('host') || '';
  headers['x-forwarded-proto'] = req.nextUrl.protocol.replace(':','');
  let body: BodyInit | undefined;
  if (!['GET','HEAD'].includes(method)) {
    const ct = req.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      const json = await req.json().catch(()=>undefined);
      body = json !== undefined ? JSON.stringify(json) : undefined;
      if (body) headers['content-type'] = 'application/json';
    } else if (ct) {
      const buf = await req.arrayBuffer();
      body = buf;
      headers['content-type'] = ct;
    }
  }
  let primaryError: any | null = null;
  const start = Date.now();
  // eslint-disable-next-line no-console
  console.log('[ClientsProxy] start', { method, target, BACKEND_BASE, hasBody: !!body, hasAuthHeader: !!req.headers.get('authorization'), userEmail: req.headers.get('x-user-email') });
  try {
    const resp = await fetch(target, { method, headers, body, redirect: 'manual' });
    const outHeaders = new Headers();
    resp.headers.forEach((v,k)=>{
      if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
      outHeaders.set(k,v);
    });
    outHeaders.set('x-proxy-target', target);
    // eslint-disable-next-line no-console
    console.log('[ClientsProxy] primary_resp', { status: resp.status, elapsedMs: Date.now() - start });
    return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
  } catch (e:any) {
    primaryError = e;
    // eslint-disable-next-line no-console
    console.log('[ClientsProxy] primary_error', { message: e?.message, elapsedMs: Date.now() - start });
  }
  // Fallback if localhost/127.* and failed
  const isLocalHost = /localhost|127\.0\.0\.1/.test(BACKEND_BASE);
  if (isLocalHost && BACKEND_BASE !== SERVICE_FALLBACK) {
    const fallbackTarget = target.replace(BACKEND_BASE, SERVICE_FALLBACK);
    try {
      // eslint-disable-next-line no-console
      console.log('[ClientsProxy] fallback_attempt', { fallbackTarget });
      const resp = await fetch(fallbackTarget, { method, headers, body, redirect: 'manual' });
      const outHeaders = new Headers();
      resp.headers.forEach((v,k)=>{
        if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
        outHeaders.set(k,v);
      });
      outHeaders.set('x-proxy-target', fallbackTarget);
      outHeaders.set('x-proxy-fallback', '1');
      // eslint-disable-next-line no-console
      console.log('[ClientsProxy] fallback_resp', { status: resp.status, elapsedMs: Date.now() - start });
      return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
    } catch (e2:any) {
      // eslint-disable-next-line no-console
      console.log('[ClientsProxy] fallback_error', { message: e2?.message, elapsedMs: Date.now() - start });
      return NextResponse.json({ error: 'Backend fetch failed (primary & fallback)', detail: e2?.message, target, fallbackTried: fallbackTarget, primaryError: primaryError?.message }, { status: 502 });
    }
  }
  return NextResponse.json({ error: 'Backend fetch failed', detail: primaryError?.message, target }, { status: 502 });
}

export async function GET(req: NextRequest) { return forward('GET', req); }
export async function POST(req: NextRequest) { return forward('POST', req); }
export async function PUT(req: NextRequest) { return forward('PUT', req); }
export async function PATCH(req: NextRequest) { return forward('PATCH', req); }
export async function DELETE(req: NextRequest) { return forward('DELETE', req); }

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

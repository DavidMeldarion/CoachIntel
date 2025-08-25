import { NextRequest, NextResponse } from 'next/server';

// Backend base (prefer internal URL inside docker, fallback to service hostname)
const RAW_BACKEND_BASE = (process.env.NEXT_PUBLIC_BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://coachintel-backend:8000');
const BACKEND_BASE = RAW_BACKEND_BASE.replace(/\/$/, '');
const SERVICE_FALLBACK = 'http://coachintel-backend:8000';

function buildUrl(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  return `${BACKEND_BASE}/clients/_debug${qs ? `?${qs}` : ''}`;
}

async function forward(req: NextRequest) {
  const target = buildUrl(req);
  const headers: Record<string,string> = {};
  req.headers.forEach((v,k)=>{
    const low = k.toLowerCase();
    if (['host','connection','content-length'].includes(low)) return;
    headers[k] = v;
  });
  headers['x-forwarded-host'] = req.headers.get('host') || '';
  headers['x-forwarded-proto'] = req.nextUrl.protocol.replace(':','');
  let primaryError: any | null = null;
  try {
    const resp = await fetch(target, { method: 'GET', headers, redirect: 'manual' });
    const outHeaders = new Headers();
    resp.headers.forEach((v,k)=>{
      if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
      outHeaders.set(k,v);
    });
    return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
  } catch (e:any) {
    primaryError = e;
  }
  const isLocalHost = /localhost|127\.0\.0\.1/.test(BACKEND_BASE);
  if (isLocalHost && BACKEND_BASE !== SERVICE_FALLBACK) {
    const fallbackTarget = target.replace(BACKEND_BASE, SERVICE_FALLBACK);
    try {
      // eslint-disable-next-line no-console
      console.log('[ClientsDebugProxy] Primary failed, retrying via service host', fallbackTarget);
      const resp = await fetch(fallbackTarget, { method: 'GET', headers, redirect: 'manual' });
      const outHeaders = new Headers();
      resp.headers.forEach((v,k)=>{
        if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
        outHeaders.set(k,v);
      });
      return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
    } catch (e2:any) {
      return NextResponse.json({ error: 'Backend fetch failed (primary & fallback)', detail: e2?.message, target, fallbackTried: fallbackTarget, primaryError: primaryError?.message }, { status: 502 });
    }
  }
  return NextResponse.json({ error: 'Backend fetch failed', detail: primaryError?.message, target }, { status: 502 });
}

export async function GET(req: NextRequest) { return forward(req); }
export const dynamic = 'force-dynamic';

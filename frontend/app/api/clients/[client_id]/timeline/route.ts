import { NextRequest, NextResponse } from 'next/server';

const RAW_BACKEND_BASE = (process.env.NEXT_PUBLIC_BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://coachintel-backend:8000');
const SERVICE_FALLBACK = 'http://coachintel-backend:8000';
// If the configured base is localhost (unreachable from inside the frontend container), switch to service host immediately
const _tmpBase = RAW_BACKEND_BASE.replace(/\/$/, '');
const BACKEND_BASE = /localhost|127\.0\.0\.1/.test(_tmpBase) ? SERVICE_FALLBACK : _tmpBase;

function buildUrl(req: NextRequest, client_id: string) {
  const qs = req.nextUrl.searchParams.toString();
  return `${BACKEND_BASE}/clients/${client_id}/timeline${qs ? `?${qs}` : ''}`;
}

async function forward(method: string, req: NextRequest, client_id: string) {
  const target = buildUrl(req, client_id);
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
    const resp = await fetch(target, { method, headers, redirect: 'manual' });
    const outHeaders = new Headers();
    resp.headers.forEach((v,k)=>{
      if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
        outHeaders.set(k,v);
    });
    return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
  } catch (e:any) {
    primaryError = e;
  }
  const isLocalHost = /localhost|127\.0\.0\.1/.test(RAW_BACKEND_BASE) && BACKEND_BASE !== SERVICE_FALLBACK;
  if (isLocalHost) {
    const fallbackTarget = target.replace(BACKEND_BASE, SERVICE_FALLBACK);
    try {
      // eslint-disable-next-line no-console
      console.log('[ClientsTimelineProxy] Primary failed, retrying via service host', fallbackTarget);
      const resp = await fetch(fallbackTarget, { method, headers, redirect: 'manual' });
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

export async function GET(req: NextRequest, ctx: any) {
  // In newer Next.js versions params may be a Promise that must be awaited
  const rawParams = ctx?.params;
  const params = rawParams && typeof rawParams.then === 'function' ? await rawParams : rawParams;
  const client_id = params?.client_id;
  if (!client_id) return NextResponse.json({ error: 'Missing client_id' }, { status: 400 });
  return forward('GET', req, client_id);
}
export const dynamic = 'force-dynamic';

import { NextRequest, NextResponse } from 'next/server';

// Determine backend base URL.
// Order of precedence:
// 1. Explicit internal URL (NEXT_PUBLIC_BACKEND_INTERNAL_URL)
// 2. Public API URL (NEXT_PUBLIC_API_URL)
// 3. Docker compose service hostname (coachintel-backend:8000) – works when frontend runs in its own container
// 4. Localhost fallback for pure local (no docker) dev
const RAW_BACKEND_BASE = (
  process.env.NEXT_PUBLIC_BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://coachintel-backend:8000'
);
const BACKEND_BASE = RAW_BACKEND_BASE.replace(/\/$/, '');
const DOCKER_SERVICE_FALLBACK = 'http://coachintel-backend:8000';
if (process.env.NODE_ENV !== 'production') {
  // Lightweight debug hint in server logs
  // eslint-disable-next-line no-console
  console.log('[Proxy] Using BACKEND_BASE =', BACKEND_BASE);
}

function buildTargetUrl(segments: string[], req: NextRequest): string {
  const path = segments.join('/');
  const qs = req.nextUrl.searchParams.toString();
  return `${BACKEND_BASE}/${path}${qs ? `?${qs}` : ''}`;
}

async function proxy(method: string, req: NextRequest, segments: string[]) {
  const target = buildTargetUrl(segments, req);
  const headers: Record<string,string> = {};
  // Forward most headers (excluding host & connection specifics)
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (['host','connection','content-length'].includes(k)) return;
    headers[key] = value;
  });
  // Ensure x-forwarded-for / host context
  headers['x-forwarded-host'] = req.headers.get('host') || '';
  headers['x-forwarded-proto'] = req.nextUrl.protocol.replace(':','');
  // Body handling for non-GET/HEAD
  let body: BodyInit | undefined = undefined;
  if (!['GET','HEAD'].includes(method)) {
    const contentType = req.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const json = await req.json().catch(() => undefined);
      body = json !== undefined ? JSON.stringify(json) : undefined;
      if (body) headers['content-type'] = 'application/json';
    } else if (contentType.includes('application/x-www-form-urlencoded') || contentType.includes('multipart/form-data')) {
      // Pass through raw arrayBuffer for form/multipart
      const buf = await req.arrayBuffer();
      body = buf;
      if (contentType) headers['content-type'] = contentType; // preserve boundary
    } else if (contentType) {
      const buf = await req.arrayBuffer();
      body = buf;
      headers['content-type'] = contentType;
    }
  }
  let resp: Response;
  try {
    resp = await fetch(target, { method, headers, body, redirect: 'manual' });
  } catch (e: any) {
    const firstErr = e;
    const isConnRefused = e?.code === 'ECONNREFUSED' || /ECONNREFUSED/i.test(e?.message || '');
    const usedLocalhost = /localhost|127\.0\.0\.1/.test(BACKEND_BASE);
    // Auto-fallback: if pointing at localhost and connection refused, try docker service hostname
    if (isConnRefused && usedLocalhost && BACKEND_BASE !== DOCKER_SERVICE_FALLBACK) {
      const altTarget = target.replace(BACKEND_BASE, DOCKER_SERVICE_FALLBACK);
      try {
        // eslint-disable-next-line no-console
        console.log('[Proxy] Primary backend unreachable, retrying via service host', altTarget);
        resp = await fetch(altTarget, { method, headers, body, redirect: 'manual' });
      } catch (e2: any) {
        const msg = 'Backend fetch failed (both primary & fallback)';
        return NextResponse.json({ error: msg, detail: e2?.message, target, fallbackTried: altTarget }, { status: 502 });
      }
    } else {
      const msg = isConnRefused ? 'Backend unreachable (connection refused)' : 'Backend fetch failed';
      return NextResponse.json({ error: msg, detail: firstErr?.message, target }, { status: 502 });
    }
  }
  // Build response
  const outHeaders = new Headers();
  resp.headers.forEach((v,k) => {
    // Strip hop-by-hop or cookie set headers (avoid cross-domain cookie confusion)
    if (['set-cookie','transfer-encoding','content-length','connection'].includes(k.toLowerCase())) return;
    outHeaders.set(k, v);
  });
  return new NextResponse(resp.body, { status: resp.status, headers: outHeaders });
}

// Some Next.js versions surface params potentially as an async value; normalize.
async function extractSegments(ctx: any): Promise<string[]> {
  try {
    const p = await ctx?.params; // handles both plain object & promise
    const segs = (p?.segments || []) as string[];
    return Array.isArray(segs) ? segs : [];
  } catch {
    return [];
  }
}

export async function GET(req: NextRequest, ctx: any) {
  const segments = await extractSegments(ctx);
  return proxy('GET', req, segments);
}
export async function POST(req: NextRequest, ctx: any) {
  const segments = await extractSegments(ctx);
  return proxy('POST', req, segments);
}
export async function PUT(req: NextRequest, ctx: any) {
  const segments = await extractSegments(ctx);
  return proxy('PUT', req, segments);
}
export async function PATCH(req: NextRequest, ctx: any) {
  const segments = await extractSegments(ctx);
  return proxy('PATCH', req, segments);
}
export async function DELETE(req: NextRequest, ctx: any) {
  const segments = await extractSegments(ctx);
  return proxy('DELETE', req, segments);
}

export const dynamic = 'force-dynamic'; // Avoid caching

// Optional debug: /api/backend/_debug to introspect proxy configuration
export async function HEAD(req: NextRequest, ctx: any) {
  const segments = await extractSegments(ctx);
  // If requesting _debug path, return config info
  if (segments.length === 1 && segments[0] === '_debug') {
    return NextResponse.json({
      backendBase: BACKEND_BASE,
      rawBackendBase: RAW_BACKEND_BASE,
      dockerFallback: DOCKER_SERVICE_FALLBACK,
      envInternal: process.env.NEXT_PUBLIC_BACKEND_INTERNAL_URL || null,
      envPublic: process.env.NEXT_PUBLIC_API_URL || null,
    });
  }
  return proxy('HEAD', req, segments);
}

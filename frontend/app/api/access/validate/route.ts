import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function getSecret() {
  const secret = process.env.ACCESS_CODE_SECRET || process.env.NEXTAUTH_SECRET;
  if (!secret) throw new Error('ACCESS_CODE_SECRET not configured');
  return secret;
}

function base64urlDecode(input: string): Buffer {
  // Node 18+ supports base64url
  return Buffer.from(input, 'base64url');
}

function verifySignature(payloadSegment: string, signatureSegment: string, secret: string) {
  const expected = crypto.createHmac('sha256', secret).update(payloadSegment).digest('base64url');
  // constant-time compare
  return crypto.timingSafeEqual(Buffer.from(signatureSegment), Buffer.from(expected));
}

function parsePayload(b64: string) {
  const buf = base64urlDecode(b64);
  try {
    return JSON.parse(buf.toString('utf8')) as { exp?: number; email?: string; id?: string };
  } catch {
    return null;
  }
}

async function validate(code: string) {
  const secret = getSecret();
  const parts = code.split('.');
  if (parts.length !== 2) return { ok: false, error: 'Malformed code' } as const;
  const [payloadSeg, signatureSeg] = parts;
  if (!verifySignature(payloadSeg, signatureSeg, secret)) {
    return { ok: false, error: 'Invalid signature' } as const;
  }
  const payload = parsePayload(payloadSeg);
  if (!payload) return { ok: false, error: 'Invalid payload' } as const;
  const now = Math.floor(Date.now() / 1000);
  if (!payload.exp || payload.exp <= now) return { ok: false, error: 'Code expired' } as const;
  return { ok: true, payload } as const;
}

export async function GET(req: NextRequest) {
  const access = req.nextUrl.searchParams.get('access') || '';
  if (!access) return NextResponse.json({ ok: false, error: 'Missing code' }, { status: 400 });
  try {
    const result = await validate(access);
    return NextResponse.json(result, { status: result.ok ? 200 : 400 });
  } catch (e: any) {
    return NextResponse.json({ ok: false, error: 'Server error' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const access = (body?.access || '').toString();
    if (!access) return NextResponse.json({ ok: false, error: 'Missing code' }, { status: 400 });
    const result = await validate(access);
    return NextResponse.json(result, { status: result.ok ? 200 : 400 });
  } catch (e: any) {
    return NextResponse.json({ ok: false, error: 'Server error' }, { status: 500 });
  }
}

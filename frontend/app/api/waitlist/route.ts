import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidPhone(phone?: string | null) {
  if (!phone) return true;
  return /^[+\d\s().-]{7,20}$/.test(phone);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const email = (body?.email || '').toString().trim().toLowerCase();
    const phone = (body?.phone || '').toString().trim();

    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: 'Invalid email' }, { status: 400 });
    }
    if (!isValidPhone(phone)) {
      return NextResponse.json({ error: 'Invalid phone' }, { status: 400 });
    }

    // TODO: Persist to your CRM or DB. For now, log to server.
    console.log('[Waitlist] New entry', { email, phone });

    return NextResponse.json({ ok: true });
  } catch (e: any) {
    return NextResponse.json({ error: 'Failed to process' }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import { getServerApiBase } from '../../../lib/serverApi';

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
    // If user is already authenticated, provide a friendly message instead of creating a waitlist entry
    const token = await getToken({ req: req as any, secret: process.env.NEXTAUTH_SECRET });
    if ((token as any)?.email) {
      return NextResponse.json(
        {
          ok: false,
          code: 'already_logged_in',
          message: "You're already signed in—no need to join the waitlist. Head to your dashboard.",
          redirect: '/dashboard',
        },
        { status: 409 }
      );
    }

    const body = await req.json().catch(() => ({}));
    const email = (body?.email || '').toString().trim().toLowerCase();
    const phone = (body?.phone || '').toString().trim();

    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: 'Invalid email' }, { status: 400 });
    }
    if (!isValidPhone(phone)) {
      return NextResponse.json({ error: 'Invalid phone' }, { status: 400 });
    }

    // Forward unauthenticated waitlist submissions to public CRM endpoint on backend
    const API_BASE = getServerApiBase();
    // Map frontend field to backend expectation for consent
    const outbound = { ...body } as any;
    // Normalize consent fields to explicit opt-in booleans for backend
    if (typeof outbound.consent_email === 'boolean') {
      outbound.consent_email_opt_in = outbound.consent_email;
      delete outbound.consent_email;
    }
    if (typeof outbound.consent_sms === 'boolean') {
      outbound.consent_sms_opt_in = outbound.consent_sms;
      delete outbound.consent_sms;
    }

    // Server-side debug logging to verify payload forwarded to backend
    try {
      console.log('[Waitlist API] Forwarding to backend /crm/public/leads:', {
        email: outbound?.email,
        hasPhone: Boolean(outbound?.phone),
        source: outbound?.source,
        utm_source: outbound?.utm_source,
        utm_medium: outbound?.utm_medium,
        utm_campaign: outbound?.utm_campaign,
        consent_email_opt_in: outbound?.consent_email_opt_in,
      });
    } catch {}

    const resp = await fetch(`${API_BASE}/crm/public/leads`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(outbound),
    });
    const text = await resp.text();
    try {
      console.log('[Waitlist API] Backend response status:', resp.status, 'body:', text);
    } catch {}
    return new NextResponse(text, {
      status: resp.status,
      headers: { 'content-type': resp.headers.get('content-type') || 'application/json' },
    });
  } catch (e: any) {
    return NextResponse.json({ error: 'Failed to process' }, { status: 500 });
  }
}

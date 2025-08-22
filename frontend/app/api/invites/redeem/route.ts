import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../../lib/serverApi';

export async function POST(request: NextRequest) {
  const API_BASE = getServerApiBase();
  const body = await request.text();
  const resp = await fetch(`${API_BASE}/invites/redeem`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

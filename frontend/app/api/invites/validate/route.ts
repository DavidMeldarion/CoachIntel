import { NextRequest, NextResponse } from 'next/server';
import { getServerApiBase } from '../../../../lib/serverApi';

export async function GET(request: NextRequest) {
  const API_BASE = getServerApiBase();
  const url = new URL(request.url);
  const token = url.searchParams.get('token') || '';
  const resp = await fetch(`${API_BASE}/invites/validate?token=${encodeURIComponent(token)}`);
  const text = await resp.text();
  return new NextResponse(text, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') || 'application/json' } });
}

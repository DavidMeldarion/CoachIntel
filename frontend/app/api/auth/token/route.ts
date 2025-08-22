import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  // Disable this debug endpoint in production
  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  const cookies = req.headers.get('cookie') || '';

  return NextResponse.json({
    cookiesSent: cookies.split(';').map(s => s.trim()).filter(Boolean),
    host: req.headers.get('host'),
    url: req.url,
    env: {
      NEXTAUTH_URL: process.env.NEXTAUTH_URL,
      NEXTAUTH_SECRET_SET: !!process.env.NEXTAUTH_SECRET,
      NODE_ENV: process.env.NODE_ENV,
    },
  });
}

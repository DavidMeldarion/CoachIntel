import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

export async function GET(req: NextRequest) {
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  const cookies = req.headers.get('cookie') || '';

  return NextResponse.json({
    hasToken: !!token,
    token,
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

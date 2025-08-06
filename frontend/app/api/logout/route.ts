import { NextResponse } from 'next/server';

export async function POST() {
  // Clear the session cookie
  console.log('[Logout API] Clearing session cookie');
  const response = NextResponse.json({ success: true });
  
  // Clear the session cookie with the exact same settings used when setting it
  const isProduction = process.env.NODE_ENV === 'production';
  
  response.cookies.set('session', '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
    sameSite: isProduction ? 'strict' : 'lax',
    secure: isProduction,
    domain: undefined, // Let browser handle domain automatically
  });
  
  console.log('[Logout API] Session cookie cleared, NODE_ENV:', process.env.NODE_ENV, 'sameSite:', isProduction ? 'strict' : 'lax');
  return response;
}

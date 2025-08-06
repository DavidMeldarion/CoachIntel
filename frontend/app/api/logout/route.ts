import { NextResponse } from 'next/server';

export async function POST() {
  // Clear the user cookie directly on frontend
  console.log('[Logout API] Clearing user cookie');
  const response = NextResponse.json({ success: true });
  
  // Clear the cookie with the exact same settings used when setting it
  response.cookies.set('user', '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    domain: undefined, // Let browser handle domain automatically
  });
  
  console.log('[Logout API] Cookie cleared, NODE_ENV:', process.env.NODE_ENV);
  return response;
}

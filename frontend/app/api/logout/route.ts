import { NextResponse } from 'next/server';

export async function POST() {
  // Clear the user cookie directly on frontend
  console.log('[Logout API] Clearing user cookie');
  const response = NextResponse.json({ success: true });
  
  // Clear the cookie with the exact same settings used when setting it
  // In production (Vercel), use strict samesite to match backend Railway settings
  const isProduction = process.env.NODE_ENV === 'production';
  
  response.cookies.set('user', '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
    sameSite: isProduction ? 'strict' : 'lax', // Match backend settings
    secure: isProduction,
    domain: undefined, // Let browser handle domain automatically
  });
  
  console.log('[Logout API] Cookie cleared, NODE_ENV:', process.env.NODE_ENV, 'sameSite:', isProduction ? 'strict' : 'lax');
  return response;
}

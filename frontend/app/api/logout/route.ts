import { NextResponse } from 'next/server';

export async function POST() {
  // Clear the user cookie directly on frontend
  const response = NextResponse.json({ success: true });
  response.cookies.set('user', '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  });
  return response;
}

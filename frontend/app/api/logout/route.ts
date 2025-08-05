import { NextResponse } from 'next/server';

export async function POST() {
  // Expire the user cookie
  const response = NextResponse.json({ success: true });
  response.cookies.set('user', '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
    sameSite: 'lax',
  });
  return response;
}

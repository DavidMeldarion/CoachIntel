import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';
import { getUserProfile } from '../lib/userApi';

// List of public routes that do not require authentication
const PUBLIC_PATHS = ['/login', '/signup', '/_next', '/favicon.ico', '/api'];

const JWT_SECRET = process.env.JWT_SECRET || 'supersecretkey';

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  // Allow public paths
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }
  // Check for user session in cookies (JWT validation)
  const userToken = request.cookies.get('user');
  if (!userToken) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }
  try {
    // jose expects a Uint8Array secret
    const secret = new TextEncoder().encode(JWT_SECRET);
    await jwtVerify(userToken.value, secret);
  } catch (err) {
    // Invalid or expired token
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }
  // After Google login, check if profile is complete
  if (userToken) {
    try {
      // Decode JWT to get email
      const secret = new TextEncoder().encode(JWT_SECRET);
      const { payload } = await jwtVerify(userToken.value, secret);
      const email = payload.sub;
      // Fetch user profile from backend
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/user/${encodeURIComponent(
          email
        )}`
      );
      if (res.ok) {
        const profile = await res.json();
        // If missing first or last name, redirect to complete-profile
        if (!profile.first_name || !profile.last_name) {
          const completeUrl = new URL('/profile/complete-profile', request.url);
          return NextResponse.redirect(completeUrl);
        }
      }
    } catch (e) {
      /* ignore, fallback to normal flow */
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|favicon.ico|api).*)'],
};

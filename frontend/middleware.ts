import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { decrypt } from './lib/session';

// Routes that require authentication
const protectedRoutes = ['/dashboard', '/profile', '/timeline', '/upload', '/apikeys'];
// Routes that should redirect to dashboard if user is authenticated
const publicRoutes = ['/login', '/signup', '/'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Skip middleware for API routes, static files, and Next.js internals
  if (
    pathname.startsWith('/api') ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Check if the current route is protected or public
  const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));
  const isPublicRoute = publicRoutes.includes(pathname);

  // Decrypt the session from the cookie
  const cookie = request.cookies.get('session')?.value;
  const session = await decrypt(cookie);

  // Redirect to /login if the user is not authenticated and trying to access protected route
  if (isProtectedRoute && !session?.userId) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect to /dashboard if the user is authenticated and trying to access public route
  if (
    isPublicRoute &&
    session?.userId &&
    !request.nextUrl.pathname.startsWith('/dashboard')
  ) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Check for profile completion requirement
  if (session?.userId && pathname !== '/profile/complete-profile') {
    try {
      // Check if user profile is complete by calling the backend
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/user/${encodeURIComponent(session.email)}`,
        {
          headers: {
            'Cookie': request.headers.get('cookie') || '',
          },
        }
      );

      if (response.ok) {
        const profile = await response.json();
        // If missing first or last name, redirect to complete-profile
        if (!profile.first_name || !profile.last_name) {
          return NextResponse.redirect(new URL('/profile/complete-profile', request.url));
        }
      }
    } catch (error) {
      // If we can't check profile, continue normally
      console.error('Profile check failed:', error);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|.*\\.png$).*)'],
};

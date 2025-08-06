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

  // Check for new session cookie first
  const sessionCookie = request.cookies.get('session')?.value;
  const session = await decrypt(sessionCookie);

  // If we have a valid new session, use it
  if (session?.userId) {
    // Redirect to /dashboard if the user is authenticated and trying to access public route
    if (isPublicRoute && !request.nextUrl.pathname.startsWith('/dashboard')) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    // Check for profile completion requirement
    if (pathname !== '/profile/complete-profile') {
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

  // If no valid new session, check for old user cookie for backward compatibility
  const oldUserCookie = request.cookies.get('user')?.value;
  
  // If user has old cookie but is trying to access protected route, redirect to login
  // This will force them to re-authenticate and get the new session format
  if (isProtectedRoute && !session?.userId) {
    // Clear old cookies to prevent confusion
    const response = NextResponse.redirect(new URL('/login', request.url));
    if (oldUserCookie) {
      response.cookies.set('user', '', { expires: new Date(0), path: '/' });
    }
    return response;
  }

  // For public routes, allow access regardless of cookie status
  // This prevents infinite redirects on login/signup pages
  if (isPublicRoute) {
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|.*\\.png$).*)'],
};

import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
  function middleware(req) {
    const { pathname } = req.nextUrl;
    const token = req.nextauth.token;

    // Routes that should redirect to dashboard if user is authenticated
    const publicRoutes = ['/signup', '/'];

    // If user is authenticated and trying to access public routes, redirect to dashboard
    if (token && publicRoutes.includes(pathname)) {
      return NextResponse.redirect(new URL('/dashboard', req.url));
    }

    // Check for profile completion requirement (optional - can be removed if not needed)
    if (token && pathname !== '/profile/complete-profile') {
      // Profile completion check can be implemented here if needed
      // For now, we'll skip this to simplify the migration
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const { pathname } = req.nextUrl;
        
        // Routes that require authentication
        const protectedRoutes = ['/dashboard', '/profile', '/timeline', '/upload', '/apikeys'];
        const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));
        
        // Public routes that don't require authentication
        const publicRoutes = ['/login', '/signup', '/'];
        const isPublicRoute = publicRoutes.includes(pathname);
        
        // Allow access to public routes regardless of auth status
        if (isPublicRoute) {
          return true;
        }
        
        // Protected routes require a valid token
        if (isProtectedRoute) {
          return !!token;
        }
        
        // Allow all other routes
        return true;
      },
    },
  }
);

export const config = {
  // Temporarily disable middleware entirely to fix redirect loop
  matcher: ['/middleware-disabled-for-debugging'],
};

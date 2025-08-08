import { withAuth } from 'next-auth/middleware';
import { NextRequest, NextResponse } from 'next/server';

// Define route types for better security and maintainability
const ROUTE_CONFIG = {
  // Public routes that anyone can access
  public: ['/', '/login', '/signup'] as string[],
  
  // Protected routes that require authentication
  protected: ['/dashboard', '/profile', '/timeline', '/upload', '/apikeys'] as string[],
  
  // API routes that should bypass middleware
  api: ['/api/auth'] as string[],
};

export default withAuth(
  function middleware(req: NextRequest & { nextauth?: { token?: any } }) {
    const { pathname } = req.nextUrl;
    const token = req.nextauth?.token;
    
    // Allow NextAuth API routes to pass through
    if (ROUTE_CONFIG.api.some(route => pathname.startsWith(route))) {
      return NextResponse.next();
    }
    
    // Check if route is protected
    const isProtectedRoute = ROUTE_CONFIG.protected.some(route => 
      pathname.startsWith(route)
    );
    
    // Check if route is public
    const isPublicRoute = ROUTE_CONFIG.public.includes(pathname);
    
    // Redirect authenticated users away from auth pages
    if (token && (pathname === '/login' || pathname === '/signup')) {
      return NextResponse.redirect(new URL('/dashboard', req.url));
    }
    
    // Redirect unauthenticated users from protected routes
    if (isProtectedRoute && !token) {
      const loginUrl = new URL('/login', req.url);
      // Preserve the original URL for redirect after login
      loginUrl.searchParams.set('callbackUrl', req.url);
      return NextResponse.redirect(loginUrl);
    }
    
    // Add security headers for all routes
    const response = NextResponse.next();
    
    // Security headers following industry best practices
    response.headers.set('X-Frame-Options', 'DENY');
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    response.headers.set('X-XSS-Protection', '1; mode=block');
    
    // Content Security Policy for enhanced security
    response.headers.set(
      'Content-Security-Policy',
      "default-src 'self'; " +
      "script-src 'self' 'unsafe-eval' 'unsafe-inline' *.vercel.com *.google.com *.gstatic.com; " +
      "style-src 'self' 'unsafe-inline' *.googleapis.com; " +
      "img-src 'self' data: *.googleusercontent.com *.google.com; " +
      "connect-src 'self' *.vercel.com *.google.com wss:; " +
      "font-src 'self' *.googleapis.com *.gstatic.com; " +
      "frame-src 'self' *.google.com;"
    );
    
    return response;
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const { pathname } = req.nextUrl;
        
        // Always allow public routes
        if (ROUTE_CONFIG.public.includes(pathname)) {
          return true;
        }
        
        // Allow API routes to be handled by their own auth
        if (ROUTE_CONFIG.api.some(route => pathname.startsWith(route))) {
          return true;
        }
        
        // For protected routes, require authentication
        const isProtectedRoute = ROUTE_CONFIG.protected.some(route => 
          pathname.startsWith(route)
        );
        
        if (isProtectedRoute) {
          return !!token;
        }
        
        // Allow all other routes (fallback)
        return true;
      },
    },
    pages: {
      signIn: '/login',
      error: '/login', // Redirect errors to login page
    },
  }
);

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - images, logos, icons (public assets)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.jpg$|.*\\.jpeg$|.*\\.gif$|.*\\.svg$).*)' 
  ],
};

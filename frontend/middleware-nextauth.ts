import { withAuth } from "next-auth/middleware"

export default withAuth(
  function middleware(req) {
    // Add any custom middleware logic here
    console.log('[Middleware] Protected route accessed:', req.nextUrl.pathname);
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        // Check if user has valid session token
        const isPublicRoute = ['/login', '/signup', '/'].includes(req.nextUrl.pathname);
        
        if (isPublicRoute) {
          return true; // Allow access to public routes
        }
        
        return !!token; // Require authentication for protected routes
      },
    },
  }
)

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/auth (NextAuth routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api/auth|_next/static|_next/image|favicon.ico).*)',
  ],
}

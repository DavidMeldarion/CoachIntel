import { withAuth } from 'next-auth/middleware';

// Use NextAuth's default middleware behavior and only match protected routes.
export default withAuth({
  pages: {
    signIn: '/login',
  },
});

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/profile/:path*',
    '/timeline/:path*',
    '/upload/:path*',
  ],
};

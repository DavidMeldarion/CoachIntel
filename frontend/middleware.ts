import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
  function middleware(req) {
    const token = (req as any).nextauth?.token as any;
    const plan = token?.plan ?? null;
    const { pathname } = req.nextUrl;

    const isPurchase = pathname.startsWith('/purchase');
    const isUpload = pathname.startsWith('/upload');

    // If trying to access Upload and not on Pro, push to purchase with Pro highlighted and a notice
    if (token && isUpload && plan !== 'pro') {
      const url = new URL('/purchase', req.url);
      url.searchParams.set('highlight', 'pro');
      if (plan) url.searchParams.set('current', plan);
      url.searchParams.set('notice', 'upload-pro-required');
      return NextResponse.redirect(url);
    }

    // If authenticated and missing a plan, force them to the purchase page
    if (token && !plan && !isPurchase) {
      return NextResponse.redirect(new URL('/purchase', req.url));
    }

    // Allow access, including visiting /purchase when a plan already exists
    return NextResponse.next();
  },
  {
    callbacks: {
      // Require a valid token to access matched routes
      authorized: ({ token }) => !!token,
    },
    pages: {
      signIn: '/login',
    },
  }
);

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/profile/:path*',
    '/timeline/:path*',
    '/upload/:path*',
    '/purchase/:path*',
    '/billing/:path*',
  ],
};

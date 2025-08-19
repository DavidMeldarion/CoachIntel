import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
  async function middleware(req) {
    const token = (req as any).nextauth?.token as any;
    const plan = token?.plan ?? null;
    const { pathname, searchParams } = req.nextUrl;

    // Owner-only admin gate
    if (pathname.startsWith('/admin')) {
      const ownerEmail = 'david@slypigdigitalmedia.com';
      if (!token || token.email !== ownerEmail) {
        return NextResponse.redirect(new URL('/dashboard', req.url));
      }
    }

    // Gate signup behind real access code validation
    if (pathname.startsWith('/signup')) {
      const access = searchParams.get('access');
      if (!access) {
        return NextResponse.redirect(new URL('/waitlist', req.url));
      }
      try {
        const validateUrl = new URL('/api/access/validate', req.url);
        validateUrl.searchParams.set('access', access);
        const r = await fetch(validateUrl.toString(), { headers: { 'x-mw': '1' } });
        if (!r.ok) {
          return NextResponse.redirect(new URL('/waitlist', req.url));
        }
        const data = await r.json().catch(() => ({}));
        if (!data?.ok) {
          return NextResponse.redirect(new URL('/waitlist', req.url));
        }
      } catch {
        return NextResponse.redirect(new URL('/waitlist', req.url));
      }
      return NextResponse.next();
    }

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
      // Allow public access to /signup (handled above), but require auth for protected routes
      authorized: ({ token, req }) => {
        const pathname = req.nextUrl.pathname;
        if (pathname.startsWith('/signup')) return true;
        return !!token;
      },
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
    '/signup/:path*',
    '/admin/:path*',
  ],
};

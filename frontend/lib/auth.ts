import { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import { getServerApiBase } from "./serverApi"

// Extend NextAuth types to include our custom fields
declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      plan?: 'free' | 'plus' | 'pro' | null;
    };
    accessToken?: string;
  }

  interface User {
    id: string;
    name?: string | null;
    email?: string | null;
    image?: string | null;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    plan?: 'free' | 'plus' | 'pro' | null;
  }
}

const isProd = process.env.NODE_ENV === 'production';

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "openid email profile https://www.googleapis.com/auth/calendar.readonly",
          access_type: "offline",
          prompt: "consent",
        },
      },
    }),
  ],
  // In dev/local HTTP, ensure the cookie is not marked Secure so the browser stores it
  cookies: {
    sessionToken: {
      name: isProd ? "__Secure-next-auth.session-token" : "next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: isProd,
      },
    },
  },
  debug: process.env.NODE_ENV !== 'production',
  logger: {
    error: (...args) => console.error('[NextAuth][error]', ...args),
    warn: (...args) => console.warn('[NextAuth][warn]', ...args),
    debug: (...args) => console.debug('[NextAuth][debug]', ...args),
  },
  callbacks: {
    async signIn({ user }) {
      console.debug('[NextAuth][signIn] start', { email: user?.email });
      try {
        const base = getServerApiBase();
        const resp = await fetch(`${base}/user/${encodeURIComponent(user.email || '')}`);
        console.debug('[NextAuth][signIn] backend /user status', resp.status);
        // Only allow sign-in if the user already exists in the backend.
        if (!resp.ok) {
          console.warn('[NextAuth][signIn] rejecting login – user not found or backend error');
          return false;
        }
      } catch (e) {
        console.warn('[NextAuth][signIn] backend check failed – rejecting login', (e as Error)?.message);
        return false;
      }
      return true; // never redirect from signIn; let session cookie be set
    },
    async jwt({ token, account, user }) {
      const base = getServerApiBase();
      if (account && user) {
        console.debug('[NextAuth][jwt] start for', user.email);
        try {
          await fetch(`${base}/auth/nextauth-sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: user.email,
              name: user.name,
              googleAccessToken: account.access_token || undefined,
              googleRefreshToken: account.refresh_token || undefined,
              googleTokenExpiry: account.expires_at ? new Date(account.expires_at * 1000).toISOString() : null,
            }),
          });
          const profileResp = await fetch(`${base}/user/${encodeURIComponent(user.email || '')}`);
          if (profileResp.ok) {
            const profile = await profileResp.json();
            (token as any).plan = profile?.plan ?? null;
            console.debug('[NextAuth][jwt] stored plan on token', (token as any).plan);
          }
        } catch (error) {
          console.warn('[NextAuth][jwt] sync failed (non-fatal)', (error as Error)?.message);
        }
        token.accessToken = account.access_token as string;
        (token as any).refreshToken = account.refresh_token;
        (token as any).expiresAt = account.expires_at;
        (token as any).email = user.email; // store for later refreshes
        (token as any).planCheckedAt = Date.now();
      } else {
        // On subsequent requests, refresh plan from backend (light TTL)
        const email = (token as any).email as string | undefined;
        const lastChecked = (token as any).planCheckedAt as number | undefined;
        const shouldRefresh = !lastChecked || Date.now() - lastChecked > 15000; // 15s TTL
        if (email && shouldRefresh) {
          try {
            const resp = await fetch(`${base}/user/${encodeURIComponent(email)}`);
            if (resp.ok) {
              const profile = await resp.json();
              (token as any).plan = profile?.plan ?? null;
              console.debug('[NextAuth][jwt] refreshed plan on token', (token as any).plan);
            }
          } catch {}
          (token as any).planCheckedAt = Date.now();
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.sub!;
        session.accessToken = token.accessToken as string;
        session.user.plan = (token.plan ?? null) as any;
        console.debug('[NextAuth][session] hydrated', { email: session.user.email, plan: session.user.plan });
      }
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  secret: process.env.NEXTAUTH_SECRET,
  session: {
    strategy: 'jwt',
    maxAge: 7 * 24 * 60 * 60,
    updateAge: 24 * 60 * 60,
  },
  jwt: {
    maxAge: 7 * 24 * 60 * 60,
  },
}

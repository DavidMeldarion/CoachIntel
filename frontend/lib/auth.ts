import { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import { getApiUrl } from "./apiUrl"

// Extend NextAuth types to include our custom fields
declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
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
  }
}

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
  callbacks: {
    async jwt({ token, account, user }) {
      // Store Google tokens and sync with backend
      if (account && user) {
        try {
          // Use internal Docker network URL for backend communication
          const backendUrl = process.env.NODE_ENV === 'development' 
            ? 'http://coachintel-backend:8000'  // Docker internal network
            : getApiUrl('');  // Production URL

          // Sync user data with backend
          const response = await fetch(`${backendUrl}/auth/nextauth-sync`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: user.email,
              name: user.name,
              googleAccessToken: account.access_token,
              googleRefreshToken: account.refresh_token,
              googleTokenExpiry: account.expires_at ? new Date(account.expires_at * 1000).toISOString() : null,
            }),
          });

          if (response.ok) {
            console.log('[NextAuth] Backend sync successful');
          } else {
            console.error('[NextAuth] Backend sync failed:', response.status);
          }
        } catch (error) {
          console.error('[NextAuth] Backend sync error:', error);
        }

        // Store tokens in JWT
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.expiresAt = account.expires_at;
      }

      return token;
    },
    async session({ session, token }) {
      // Add custom fields to session
      if (session.user) {
        session.user.id = token.sub!;
        session.accessToken = token.accessToken as string;
      }
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 7 * 24 * 60 * 60, // 7 days
    updateAge: 24 * 60 * 60, // Update session every 24 hours
  },
  jwt: {
    maxAge: 7 * 24 * 60 * 60, // 7 days
    secret: process.env.NEXTAUTH_SECRET,
  },
  cookies: {
    sessionToken: {
      name: 'next-auth.session-token',
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
        domain: process.env.NODE_ENV === 'production' ? '.coachintel.ai' : undefined,
      },
    },
    callbackUrl: {
      name: 'next-auth.callback-url',
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },
  events: {
    async signIn({ user, account, profile }) {
      console.log(`[NextAuth] User signed in: ${user.email}`);
    },
    async signOut({ token }) {
      console.log(`[NextAuth] User signed out`);
    },
    async session({ session, token }) {
      // Log session access for security monitoring
      console.log(`[NextAuth] Session accessed for user: ${session.user?.email}`);
    },
  },
}

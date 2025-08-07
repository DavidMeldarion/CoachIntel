// Force correct NEXTAUTH_URL before importing NextAuth
if (process.env.NODE_ENV === 'production') {
  process.env.NEXTAUTH_URL = 'https://www.coachintel.ai/frontend';
  process.env.NEXTAUTH_URL_INTERNAL = 'https://www.coachintel.ai/frontend';
}

import NextAuth from "next-auth"
import { authOptions } from "../../../../lib/auth"

console.log('[NextAuth Route] Loading NextAuth handler - production debug');
console.log('[NextAuth Route] NEXTAUTH_URL:', process.env.NEXTAUTH_URL);
console.log('[NextAuth Route] NEXTAUTH_URL_INTERNAL:', process.env.NEXTAUTH_URL_INTERNAL);

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }

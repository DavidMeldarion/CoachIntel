import NextAuth from "next-auth"
import { authOptions } from "../../../../lib/auth"

console.log('[NextAuth Route] Loading NextAuth handler - production debug');
console.log('[NextAuth Route] NEXTAUTH_URL:', process.env.NEXTAUTH_URL);

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }

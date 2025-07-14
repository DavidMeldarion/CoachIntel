import { NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

const JWT_SECRET = process.env.JWT_SECRET || 'supersecretkey';

export async function GET(request: Request) {
  const cookie = request.headers.get('cookie') || '';
  const match = cookie.match(/(?:^|; )user=([^;]+)/);
  if (!match) {
    return NextResponse.json({ loggedIn: false });
  }
  try {
    const secret = new TextEncoder().encode(JWT_SECRET);
    await jwtVerify(match[1], secret);
    return NextResponse.json({ loggedIn: true });
  } catch {
    return NextResponse.json({ loggedIn: false });
  }
}

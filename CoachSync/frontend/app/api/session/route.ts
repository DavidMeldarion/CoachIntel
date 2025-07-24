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
    const { payload } = await jwtVerify(match[1], secret);
    
    // Fetch user information from backend
    try {
      const backendResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/me`, {
        headers: {
          'Cookie': `user=${match[1]}`
        }
      });      if (backendResponse.ok) {
        const userData = await backendResponse.json();
        
        return NextResponse.json({ 
          loggedIn: true, 
          user: {
            email: userData.email,
            first_name: userData.first_name,
            last_name: userData.last_name,
            name: userData.name, // Keep for backward compatibility
            fireflies_api_key: userData.fireflies_api_key,
            zoom_jwt: userData.zoom_jwt,
            phone: userData.phone,
            address: userData.address,
          }
        });
      } else {
        console.error('Backend response not ok:', backendResponse.status, backendResponse.statusText);
      }
    } catch (error) {
      console.error('Failed to fetch user data:', error);
    }
      // Fallback: just return logged in status with email from JWT
    return NextResponse.json({ 
      loggedIn: true, 
      user: { 
        email: payload.sub,
        first_name: null,
        last_name: null,
        name: null 
      }
    });
  } catch {
    return NextResponse.json({ loggedIn: false });
  }
}

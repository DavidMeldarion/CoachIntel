import { NextResponse } from 'next/server';

export async function POST() {
  // Forward logout request to backend to properly clear cookie
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BROWSER_API_URL || 'http://localhost:8000';
    const cleanBaseUrl = backendUrl.replace(/\/+$/, '');
    const logoutUrl = `${cleanBaseUrl}/logout`;
    
    const response = await fetch(logoutUrl, {
      method: 'POST',
      credentials: 'include',
    });
    
    if (response.ok) {
      return NextResponse.json({ success: true });
    } else {
      return NextResponse.json({ success: false, error: 'Backend logout failed' }, { status: 500 });
    }
  } catch (error) {
    console.error('Logout error:', error);
    return NextResponse.json({ success: false, error: 'Logout failed' }, { status: 500 });
  }
}

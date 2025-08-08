import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  // Disable in production
  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  const url = new URL(request.url);
  const error = url.searchParams.get('error');
  const errorDescription = url.searchParams.get('error_description');
  const callbackUrl = url.searchParams.get('callbackUrl');
  
  return NextResponse.json({ 
    message: 'NextAuth Error Debug',
    timestamp: new Date().toISOString(),
    error: error,
    errorDescription: errorDescription,
    callbackUrl: callbackUrl,
    fullUrl: request.url,
    env: {
      NEXTAUTH_URL: process.env.NEXTAUTH_URL,
      GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID ? 'SET' : 'NOT_SET',
    },
    possibleIssues: [
      'Google OAuth redirect URI mismatch',
      'Invalid Google Client ID or Secret',
      'NEXTAUTH_URL configuration issue',
      'Cookie domain issues'
    ]
  })
}

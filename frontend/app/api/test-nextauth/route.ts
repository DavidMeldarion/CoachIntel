import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const baseUrl = new URL(request.url).origin;
  
  // Test different NextAuth endpoints
  const endpoints = [
    '/frontend/api/auth/providers',
    '/frontend/api/auth/session',
    '/frontend/api/auth/csrf',
    '/api/auth/providers',
    '/api/auth/session',
    '/api/auth/csrf',
  ];
  
  const results = [];
  
  for (const endpoint of endpoints) {
    try {
      const testUrl = `${baseUrl}${endpoint}`;
      const response = await fetch(testUrl, { 
        method: 'HEAD',
        headers: {
          'User-Agent': 'NextAuth-Test'
        }
      });
      results.push({
        endpoint,
        status: response.status,
        accessible: response.status !== 404
      });
    } catch (error) {
      results.push({
        endpoint,
        status: 'ERROR',
        accessible: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }
  
  return NextResponse.json({ 
    message: 'NextAuth Endpoint Test',
    timestamp: new Date().toISOString(),
    baseUrl,
    results,
    env: {
      NEXTAUTH_URL: process.env.NEXTAUTH_URL,
      NODE_ENV: process.env.NODE_ENV,
    }
  })
}

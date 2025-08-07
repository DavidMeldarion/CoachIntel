import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const baseUrl = new URL(request.url).origin;
  
  // Test actual NextAuth endpoints with proper headers
  const endpoints = [
    {
      url: '/frontend/api/auth/providers',
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    },
    {
      url: '/frontend/api/auth/session',
      method: 'GET', 
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    },
    {
      url: '/frontend/api/auth/csrf',
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    }
  ];
  
  const results = [];
  
  for (const endpoint of endpoints) {
    try {
      const testUrl = `${baseUrl}${endpoint.url}`;
      const response = await fetch(testUrl, {
        method: endpoint.method,
        headers: endpoint.headers
      });
      
      let responseData = null;
      try {
        responseData = await response.text();
      } catch (e) {
        responseData = 'Could not read response';
      }
      
      results.push({
        endpoint: endpoint.url,
        status: response.status,
        statusText: response.statusText,
        accessible: response.status < 400,
        headers: Object.fromEntries(response.headers.entries()),
        data: responseData.substring(0, 200) // First 200 chars only
      });
    } catch (error) {
      results.push({
        endpoint: endpoint.url,
        status: 'ERROR',
        accessible: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }
  
  return NextResponse.json({ 
    message: 'NextAuth Detailed Test',
    timestamp: new Date().toISOString(),
    baseUrl,
    results
  })
}

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  return NextResponse.json({ 
    message: 'API routes are working',
    timestamp: new Date().toISOString(),
    url: request.url 
  })
}

export async function POST(request: NextRequest) {
  return NextResponse.json({ 
    message: 'API routes are working - POST',
    timestamp: new Date().toISOString() 
  })
}

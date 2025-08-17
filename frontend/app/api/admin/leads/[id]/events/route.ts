import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json({ error: 'Not implemented' }, { status: 404 })
}

// Optional: explicitly disallow other methods
export async function POST() {
  return NextResponse.json({ error: 'Method not allowed' }, { status: 405 })
}

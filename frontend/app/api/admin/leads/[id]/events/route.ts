export const dynamic = 'force-dynamic'

export async function GET() {
  return new Response(JSON.stringify({ error: 'Not implemented' }), {
    status: 404,
    headers: { 'content-type': 'application/json' },
  })
}

export async function POST() {
  return new Response(JSON.stringify({ error: 'Method not allowed' }), {
    status: 405,
    headers: { 'content-type': 'application/json' },
  })
}

export const dynamic = 'force-dynamic'

export async function POST() {
  return new Response(JSON.stringify({ error: 'Not implemented' }), {
    status: 404,
    headers: { 'content-type': 'application/json' },
  })
}

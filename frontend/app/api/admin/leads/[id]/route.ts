export const dynamic = 'force-dynamic'

export async function GET(request: Request, context: any) {
  try {
    const id = context?.params?.id as string
    const res = await fetch(`/api/leads/${encodeURIComponent(id)}`, { cache: 'no-store' })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'content-type': res.headers.get('content-type') || 'application/json' },
    })
  } catch {
    return new Response(JSON.stringify({ error: 'Not implemented' }), {
      status: 404,
      headers: { 'content-type': 'application/json' },
    })
  }
}

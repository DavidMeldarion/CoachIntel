export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const url = new URL(request.url)
  const qp = url.search
  const res = await fetch(`/api/leads${qp}`, { cache: 'no-store' })
  const body = await res.text()
  return new Response(body, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
}

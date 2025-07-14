import type { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  const key = req.nextUrl.searchParams.get("key");
  if (!key) return new Response("Missing key", { status: 400 });
  // Proxy to backend
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendUrl}/external-meetings/?source=fireflies&user=test@demo.com`;
  const res = await fetch(url, { headers: { "x-api-key": key } });
  return new Response(null, { status: res.ok ? 200 : 400 });
}

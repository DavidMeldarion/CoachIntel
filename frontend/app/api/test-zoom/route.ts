import type { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  const jwt = req.nextUrl.searchParams.get("jwt");
  if (!jwt) return new Response("Missing jwt", { status: 400 });
  // Proxy to backend
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendUrl}/external-meetings/?source=zoom&user=test_user_id`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${jwt}` } });
  return new Response(null, { status: res.ok ? 200 : 400 });
}

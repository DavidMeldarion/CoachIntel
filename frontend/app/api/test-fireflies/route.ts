import type { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  // Proxy to backend, using session cookie for authentication
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendUrl}/test-fireflies`;
  // Forward cookies for session
  const cookie = req.headers.get("cookie") || "";
  const res = await fetch(url, {
    method: "GET",
    headers: { "cookie": cookie },
    credentials: "include",
  });
  if (res.ok) {
    return new Response(null, { status: 200 });
  } else {
    return new Response(await res.text(), { status: 400 });
  }
}

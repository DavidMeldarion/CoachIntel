import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";
import { getServerApiBase } from "../../../lib/serverApi";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  const session = await getServerSession(authOptions);
  const email = session?.user?.email || null;

  if (!email) {
    return new Response(JSON.stringify({ detail: "No session or email in session" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Use internal URL inside Docker for server-to-server calls
  const API_BASE = getServerApiBase();
  const url = `${API_BASE}/test-fireflies`;
  const cookie = req.headers.get("cookie") || "";

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        ...(cookie ? { cookie } : {}),
        "x-user-email": email,
        authorization: `Bearer ${email}`,
      },
    });

    if (res.ok) {
      return new Response(null, { status: 200 });
    }

    const body = await res.text();
    return new Response(body, { status: res.status });
  } catch (err: any) {
    console.error("[test-fireflies] Backend fetch failed:", err?.message || err);
    return new Response("Backend unreachable from frontend. Check INTERNAL_API_URL and docker networking.", { status: 502 });
  }
}

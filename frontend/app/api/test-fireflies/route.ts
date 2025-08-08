import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";

export async function GET(req: Request) {
  const session = await getServerSession(authOptions);
  const email = session?.user?.email || null;

  if (!email) {
    return new Response(JSON.stringify({ detail: "No session or email in session" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://coachintel-backend:8000";
  const url = `${API_BASE}/test-fireflies`;
  const cookie = req.headers.get("cookie") || "";

  const res = await fetch(url, {
    method: "GET",
    headers: {
      ...(cookie ? { cookie } : {}),
      "x-user-email": email,
      authorization: `Bearer ${email}`,
    },
    credentials: "include",
  });

  if (res.ok) {
    return new Response(null, { status: 200 });
  }

  const body = await res.text();
  return new Response(body, { status: res.status });
}

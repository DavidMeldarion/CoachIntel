import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../../lib/auth";
import { getServerApiBase } from "../../../../lib/serverApi";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: Request, context: any) {
  const session = await getServerSession(authOptions);
  const email = session?.user?.email || null;
  if (!email) {
    return new Response(JSON.stringify({ detail: "No session or email in session" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }
  const meetingId = context?.params?.meetingId as string;
  const API_BASE = getServerApiBase();
  const url = `${API_BASE}/meetings/${encodeURIComponent(meetingId)}`;
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
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    console.error("[meetings/:id] Backend fetch failed:", err?.message || err);
    return new Response("Backend unreachable", { status: 502 });
  }
}

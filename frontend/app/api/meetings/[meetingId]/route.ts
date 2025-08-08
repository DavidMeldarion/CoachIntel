import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../../lib/auth";

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
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://coachintel-backend:8000";
  const url = `${backendUrl}/meetings/${encodeURIComponent(meetingId)}`;
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
  const data = await res.json();
  return new Response(JSON.stringify(data), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

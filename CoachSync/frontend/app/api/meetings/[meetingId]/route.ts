import type { NextRequest } from "next/server";

export async function GET(req: NextRequest, { params }: { params: { meetingId: string } }) {
  const meetingId = params.meetingId;
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendUrl}/meetings/${encodeURIComponent(meetingId)}`;
  // Forward cookies for session authentication
  const cookie = req.headers.get("cookie") || "";
  const res = await fetch(url, {
    method: "GET",
    headers: { "cookie": cookie },
    credentials: "include"
  });
  const data = await res.json();
  return new Response(JSON.stringify(data), {
    status: res.status,
    headers: { "Content-Type": "application/json" }
  });
}

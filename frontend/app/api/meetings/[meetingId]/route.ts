export async function GET(req: Request, context: any) {
  const meetingId = context?.params?.meetingId as string;
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendUrl}/meetings/${encodeURIComponent(meetingId)}`;
  const cookie = req.headers.get("cookie") || "";
  const res = await fetch(url, {
    method: "GET",
    headers: { ...(cookie ? { cookie } : {}) },
    credentials: "include",
  });
  const data = await res.json();
  return new Response(JSON.stringify(data), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

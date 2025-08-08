import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const email = session?.user?.email || null;
  if (!email) {
    return NextResponse.json({ detail: "No session or email in session" }, { status: 401 });
  }
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://coachintel-backend:8000";
  const backendUrl = `${API_BASE}/summarize-missing-transcripts`;
  const cookie = request.headers.get("cookie") || "";
  const res = await fetch(backendUrl, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(cookie ? { cookie } : {}),
      "x-user-email": email,
      authorization: `Bearer ${email}`,
    },
  });
  let data;
  try {
    data = await res.json();
  } catch {
    return NextResponse.json({ error: "Backend returned non-JSON response" }, { status: 500 });
  }
  return NextResponse.json(data, { status: res.status });
}

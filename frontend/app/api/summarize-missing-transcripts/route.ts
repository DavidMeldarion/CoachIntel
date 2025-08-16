import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";
import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../lib/serverApi";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const email = session?.user?.email || null;
  if (!email) {
    return NextResponse.json({ detail: "No session or email in session" }, { status: 401 });
  }
  const API_BASE = getServerApiBase();
  const backendUrl = `${API_BASE}/summarize-missing-transcripts`;
  const cookie = request.headers.get("cookie") || "";
  try {
    const res = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(cookie ? { cookie } : {}),
        "x-user-email": email,
        authorization: `Bearer ${email}`,
      },
    });
    let data: any = null;
    try {
      data = await res.json();
    } catch {
      return NextResponse.json({ error: "Backend returned non-JSON response" }, { status: 500 });
    }
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    console.error("[summarize-missing-transcripts] Backend fetch failed:", err?.message || err);
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}

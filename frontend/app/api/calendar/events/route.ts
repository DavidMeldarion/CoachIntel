import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../../lib/auth";
import { getServerApiBase } from "../../../../lib/serverApi";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const email = session?.user?.email || null;
  if (!email) {
    return NextResponse.json({ detail: "No session or email in session" }, { status: 401 });
  }
  const cookie = request.headers.get("cookie") || "";
  const API_BASE = getServerApiBase();
  const backendUrl = `${API_BASE}/calendar/events`;
  try {
    const response = await fetch(backendUrl, {
      headers: {
        ...(cookie ? { cookie } : {}),
        "x-user-email": email,
        authorization: `Bearer ${email}`,
      },
    });
    let data;
    try {
      data = await response.clone().json(); // Use clone to avoid double-read errors
    } catch (err) {
      const text = await response.text();
      return NextResponse.json({ error: "Internal Server Error", detail: text }, { status: 500 });
    }
    return NextResponse.json(data, { status: response.status });
  } catch (err: any) {
    console.error("[calendar/events] Backend fetch failed:", err?.message || err);
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}

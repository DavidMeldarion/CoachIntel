import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";
import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../lib/serverApi";

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
  const backendUrl = `${API_BASE}/meetings`;
  try {
    const response = await fetch(backendUrl, {
      headers: {
        ...(cookie ? { cookie } : {}),
        "x-user-email": email,
        authorization: `Bearer ${email}`,
      },
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (err: any) {
    console.error("[meetings] Backend fetch failed:", err?.message || err);
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}

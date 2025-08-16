import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";
import { getServerApiBase } from "../../../lib/serverApi";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Only POST is supported for sync
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    const email = session?.user?.email || null;
    if (!email) {
      return NextResponse.json(
        { detail: "No session or email in session" },
        { status: 401 }
      );
    }

    // Accept source from body or query for robustness
    let source: string | null = null;
    try {
      const body = await request.json();
      source = body?.source ?? null;
    } catch {
      // ignore JSON parse errors; may not have a body
    }
    if (!source) {
      source = request.nextUrl.searchParams.get("source");
    }
    if (!source) {
      return NextResponse.json(
        { error: "Missing required parameter: source" },
        { status: 400 }
      );
    }

    const API_BASE = getServerApiBase();
    const url = new URL("/sync/external-meetings", API_BASE);
    url.searchParams.set("source", source);

    const cookie = request.headers.get("cookie") || "";
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        ...(cookie ? { cookie } : {}),
        "x-user-email": email,
        authorization: `Bearer ${email}`,
      },
    });

    // Pass through backend JSON and status
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error("[external-meetings] Error:", error?.message || error);
    return NextResponse.json(
      { error: "Failed to sync meetings" },
      { status: 500 }
    );
  }
}

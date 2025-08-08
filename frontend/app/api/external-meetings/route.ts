import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";

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
    const body = await request.json();
    const source = body.source;
    if (!source) {
      return NextResponse.json(
        { error: "Missing required parameter: source" },
        { status: 400 }
      );
    }
    const API_BASE =
      process.env.NEXT_PUBLIC_API_URL || "http://coachintel-backend:8000";
    const backendUrl = `${API_BASE}/sync/external-meetings?source=${source}`;
    const cookie = request.headers.get("cookie");
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(cookie ? { cookie } : {}),
        "x-user-email": email,
        authorization: `Bearer ${email}`,
      },
      credentials: "include",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Error syncing external meetings:", error);
    return NextResponse.json(
      { error: "Failed to sync meetings" },
      { status: 500 }
    );
  }
}

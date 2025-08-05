import { NextRequest, NextResponse } from "next/server";

// Only POST is supported for sync
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const source = body.source;
    if (!source) {
      return NextResponse.json(
        { error: "Missing required parameter: source" },
        { status: 400 }
      );
    }
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://coachintel-backend:8000";
    const backendUrl = `${API_BASE}/sync/external-meetings?source=${source}`;
    const cookie = request.headers.get("cookie");
    // console.log("[API DEBUG] Sync backend URL:", backendUrl);
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(cookie ? { cookie } : {}),
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

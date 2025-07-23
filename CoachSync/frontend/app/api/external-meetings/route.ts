import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    // Use URL to extract query params only
    const { searchParams } = new URL(request.url);
    const source = searchParams.get("source");
    const limit = searchParams.get("limit") || "10";

    if (!source) {
      return NextResponse.json(
        { error: "Missing required parameter: source" },
        { status: 400 }
      );
    }

    // Always use the backend base URL and endpoint path directly
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    const backendUrl = `${API_BASE}/external-meetings/?source=${source}&limit=${limit}`;

    // Extract the 'user' cookie from the incoming request and forward it to the backend
    const cookie = request.headers.get("cookie");

    console.log("[API DEBUG] Fetching backend URL:", backendUrl);
    const response = await fetch(backendUrl, {
      headers: {
        ...(cookie ? { cookie } : {}),
      },
      credentials: "include",
    });

    // Forward the full backend response (may include task_id for polling)
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Error fetching external meetings:", error);
    return NextResponse.json(
      { error: "Failed to fetch meetings" },
      { status: 500 }
    );
  }
}

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
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    const backendUrl = `${API_BASE}/sync/external-meetings?source=${source}`;
    const cookie = request.headers.get("cookie");
    console.log("[API DEBUG] Sync backend URL:", backendUrl);
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(cookie ? { cookie } : {}),
      },
      credentials: "include",
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error syncing external meetings:", error);
    return NextResponse.json(
      { error: "Failed to sync meetings" },
      { status: 500 }
    );
  }
}

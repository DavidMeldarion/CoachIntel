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

    const response = await fetch(backendUrl, {
      headers: {
        ...(cookie ? { cookie } : {}),
      },
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching external meetings:", error);
    return NextResponse.json(
      { error: "Failed to fetch meetings" },
      { status: 500 }
    );
  }
}

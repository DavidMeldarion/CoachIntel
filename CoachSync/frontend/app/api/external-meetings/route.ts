import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const source = searchParams.get("source");
    const user = searchParams.get("user");
    const limit = searchParams.get("limit") || "10";

    if (!source || !user) {
      return NextResponse.json(
        { error: "Missing required parameters: source and user" },
        { status: 400 }
      );
    }

    // Get the user's Fireflies API key from their profile
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    
    // For now, we'll use the backend directly
    // In a real app, you'd get the API key from the user's profile
    const response = await fetch(
      `${API_BASE}/external-meetings/?source=${source}&user=${encodeURIComponent(user)}&limit=${limit}`,
      {
        headers: {
          // Forward any authorization headers
          ...request.headers,
        },
      }
    );

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

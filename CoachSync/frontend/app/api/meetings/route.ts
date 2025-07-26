import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  // Forward the user's cookie to the backend
  const cookie = request.headers.get("cookie");
  // Use the correct backend URL for server-side fetches
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
  const backendUrl = `${API_BASE}/meetings`;
  const response = await fetch(backendUrl, {
    headers: {
      ...(cookie ? { cookie } : {}),
    },
    credentials: "include",
  });
  const data = await response.json();
  return NextResponse.json(data);
}

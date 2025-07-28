import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  // Extract task_id from the URL
  const task_id = request.nextUrl.pathname.split("/").pop();
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
  const backendUrl = `${API_BASE}/sync/status/${task_id}`;
  const response = await fetch(backendUrl, {
    credentials: "include",
    cache: "no-store" // Explicitly disable caching at the Next.js API route level
  });
  let data;
  try {
    data = await response.json();
    // console.log("[SYNC STATUS API] Backend response:", data);
  } catch {
    // If not JSON, return a generic error
    console.error("[SYNC STATUS API] Backend returned non-JSON response", response.status);
    return NextResponse.json(
      { error: "Backend returned non-JSON response", status: response.status },
      { status: response.status, headers: { "Cache-Control": "no-store" } }
    );
  }
  return NextResponse.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } });
}

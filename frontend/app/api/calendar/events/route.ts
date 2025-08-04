import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const cookie = request.headers.get("cookie");
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://coachintel-backend:8000";
  const backendUrl = `${API_BASE}/calendar/events`;
  const response = await fetch(backendUrl, {
    headers: {
      ...(cookie ? { cookie } : {}),
    },
    credentials: "include",
  });
  let data;
  try {
    data = await response.clone().json(); // Use clone to avoid double-read errors
  } catch (err) {
    const text = await response.text();
    return NextResponse.json({ error: "Internal Server Error", detail: text }, { status: 500 });
  }
  return NextResponse.json(data, { status: response.status });
}

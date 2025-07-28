import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const backendUrl = `${API_BASE}/summarize-missing-transcripts`;
  const res = await fetch(backendUrl, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  let data;
  try {
    data = await res.json();
  } catch {
    return NextResponse.json({ error: "Backend returned non-JSON response" }, { status: 500 });
  }
  return NextResponse.json(data, { status: res.status });
}

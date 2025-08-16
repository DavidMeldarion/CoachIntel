import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../../lib/serverApi";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  // Extract task_id from the URL
  const task_id = request.nextUrl.pathname.split("/").pop();
  const API_BASE = getServerApiBase();
  const backendUrl = `${API_BASE}/sync/status/${task_id}`;
  try {
    const response = await fetch(backendUrl, {
      cache: "no-store",
    });
    let data;
    try {
      data = await response.json();
    } catch {
      console.error("[SYNC STATUS API] Backend returned non-JSON response", response.status);
      return NextResponse.json(
        { error: "Backend returned non-JSON response", status: response.status },
        { status: response.status, headers: { "Cache-Control": "no-store" } }
      );
    }
    return NextResponse.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch (err: any) {
    console.error("[SYNC STATUS API] Backend fetch failed:", err?.message || err);
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}

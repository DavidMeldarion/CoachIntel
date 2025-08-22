import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../../lib/serverApi";

// Local RouteContext alias
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
type RouteContext<TPath extends string> = { params: Promise<Record<string,string>> }

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest, ctx: RouteContext<'/api/sync/status/[task_id]'>) {
  const { task_id } = await ctx.params as any
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

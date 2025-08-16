import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { getToken } from "next-auth/jwt";
import { authOptions } from "../../../lib/auth";
import { cookies as nextCookies } from "next/headers";
import { getServerApiBase } from "../../../lib/serverApi";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const email = session?.user?.email || token?.email || null;

  const cookieStore = await nextCookies();
  const cookieHeader = cookieStore.getAll().map((c: any) => `${c.name}=${c.value}`).join("; ");

  const API_BASE = getServerApiBase();
  try {
    const resp = await fetch(`${API_BASE}/me`, {
      method: "GET",
      headers: {
        ...(cookieHeader ? { cookie: cookieHeader } : {}),
        ...(email ? { "x-user-email": email, authorization: `Bearer ${email}` } : {}),
      },
      credentials: "include",
    });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: "Backend unreachable", detail: err?.message },
      { status: 502 }
    );
  }
}

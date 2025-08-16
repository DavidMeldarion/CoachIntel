import { getServerSession } from "next-auth";
import { getToken } from "next-auth/jwt";
import { authOptions } from "../../../lib/auth";
import { NextRequest, NextResponse } from "next/server";
import { cookies as nextCookies } from "next/headers";
import { getServerApiBase } from "../../../lib/serverApi";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getApiBase(): string {
  return getServerApiBase();
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const emailFromQuery = url.searchParams.get("email");
  const session = await getServerSession(authOptions);
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const email = emailFromQuery || session?.user?.email || token?.email || null;
  if (!email) return NextResponse.json({ error: "No email provided" }, { status: 400 });

  const API_BASE = getApiBase();
  const resp = await fetch(`${API_BASE}/user/${encodeURIComponent(email)}`);
  const data = await resp.json().catch(() => ({}));
  return NextResponse.json(data, { status: resp.status });
}

export async function PUT(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const clientEmail = request.headers.get("x-user-email");
  const email = session?.user?.email || token?.email || clientEmail || null;

  // Build Cookie header from server cookies API (await for Next 15)
  const cookieStore = await nextCookies();
  const cookieHeader = cookieStore.getAll().map((c: any) => `${c.name}=${c.value}`).join("; ");

  console.log("[User API] PUT request received", {
    hasSession: !!session,
    hasToken: !!token,
    clientEmail: !!clientEmail,
    hasCookie: cookieHeader.length > 0,
    email,
  });

  if (!email) {
    return NextResponse.json({ detail: "No session or email in session" }, { status: 401 });
  }

  const API_BASE = getApiBase();
  const backendUrl = `${API_BASE}/user`;

  const body = await request.text();
  console.log("[User API] PUT → backend", { backendUrl, hasCookie: cookieHeader.length > 0, email });

  try {
    const response = await fetch(backendUrl, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...(cookieHeader ? { cookie: cookieHeader } : {}),
        "x-user-email": email,
        authorization: `Bearer ${email}`,
      },
      credentials: "include",
      body,
    });

    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch (err: any) {
    console.error("[User API] backend fetch failed", err?.message);
    return NextResponse.json(
      { error: "Backend unreachable", detail: err?.message, backendUrl },
      { status: 502 }
    );
  }
}

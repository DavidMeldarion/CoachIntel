import { getServerSession } from "next-auth/next";
import { authOptions } from "../../../lib/auth";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const email = session?.user?.email || null;
  if (!email) {
    return NextResponse.json({ detail: "No session or email in session" }, { status: 401 });
  }

  const cookie = request.headers.get("cookie");
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://coachintel-backend:8000";
  const backendUrl = `${API_BASE}/meetings`;
  const response = await fetch(backendUrl, {
    headers: {
      ...(cookie ? { cookie } : {}),
      "x-user-email": email,
      authorization: `Bearer ${email}`,
    },
    credentials: "include",
  });
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}

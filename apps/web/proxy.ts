import { NextRequest, NextResponse } from "next/server";

import { defaultLocale, isLocale } from "@/lib/i18n";

// Runtime API proxy. Next.js rewrites() are evaluated at BUILD time and cannot
// read Render's runtime API_INTERNAL_URL, so we proxy /api/v1/* here at request
// time instead. The running server DOES have API_INTERNAL_URL available.
const API_TARGET = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

async function proxyApi(request: NextRequest): Promise<NextResponse> {
  const { pathname, search } = request.nextUrl;
  const target = `${API_TARGET}${pathname}${search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("keep-alive");

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer().catch(() => undefined);

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
      cache: "no-store",
    });
    const responseHeaders = new Headers(upstream.headers);
    for (const hop of ["connection", "keep-alive", "transfer-encoding", "content-encoding"]) {
      responseHeaders.delete(hop);
    }
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (err) {
    return new NextResponse(
      JSON.stringify({ detail: "API gateway unreachable", error: String(err) }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // API calls: proxy to the live backend at runtime.
  if (pathname.startsWith("/api/v1/")) {
    return proxyApi(request);
  }

  const firstSegment = pathname.split("/")[1];

  if (firstSegment && isLocale(firstSegment)) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-kalibr-locale", firstSegment);
    return NextResponse.next({ request: { headers: requestHeaders } });
  }

  const redirectUrl = request.nextUrl.clone();
  redirectUrl.pathname = `/${defaultLocale}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(redirectUrl);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt).*)"],
};

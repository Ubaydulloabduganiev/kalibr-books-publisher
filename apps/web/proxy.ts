import { timingSafeEqual } from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

import { defaultLocale, isLocale } from "@/lib/i18n";

function apiTarget(): string {
  const raw = process.env.API_INTERNAL_URL?.trim().replace(/\/+$/, "");
  if (!raw) return "http://127.0.0.1:8000";
  return /^https?:\/\//i.test(raw) ? raw : `http://${raw}`;
}

function equalSecret(actual: string, expected: string): boolean {
  const actualBuffer = Buffer.from(actual);
  const expectedBuffer = Buffer.from(expected);
  return actualBuffer.length === expectedBuffer.length && timingSafeEqual(actualBuffer, expectedBuffer);
}

function basicAuthAllowed(request: NextRequest): boolean {
  const expectedUser = process.env.ADMIN_BASIC_USERNAME;
  const expectedPassword = process.env.ADMIN_BASIC_PASSWORD;
  if (!expectedUser || !expectedPassword) return process.env.NODE_ENV !== "production";

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Basic ")) return false;
  try {
    const decoded = Buffer.from(authorization.slice(6), "base64").toString("utf8");
    const separator = decoded.indexOf(":");
    if (separator < 0) return false;
    return (
      equalSecret(decoded.slice(0, separator), expectedUser) &&
      equalSecret(decoded.slice(separator + 1), expectedPassword)
    );
  } catch {
    return false;
  }
}

function unauthorized(): NextResponse {
  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "Cache-Control": "no-store",
      "WWW-Authenticate": 'Basic realm="Kalibr Publisher", charset="UTF-8"',
    },
  });
}

async function proxyApi(request: NextRequest): Promise<NextResponse> {
  const target = `${apiTarget()}${request.nextUrl.pathname}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  for (const header of [
    "authorization",
    "host",
    "connection",
    "keep-alive",
    "transfer-encoding",
    "x-internal-api-key",
  ]) {
    headers.delete(header);
  }
  const internalKey = process.env.INTERNAL_API_KEY;
  if (internalKey) headers.set("X-Internal-API-Key", internalKey);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const isUpload = request.nextUrl.pathname === "/api/v1/posts/upload";
  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    redirect: "manual",
    cache: "no-store",
    signal: AbortSignal.timeout(isUpload ? 10 * 60_000 : 60_000),
  };
  if (hasBody) init.duplex = "half";

  try {
    const upstream = await fetch(target, init);
    const responseHeaders = new Headers(upstream.headers);
    for (const header of ["connection", "keep-alive", "transfer-encoding"]) {
      responseHeaders.delete(header);
    }
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("API gateway unreachable", {
      errorType: error instanceof Error ? error.name : "UnknownError",
    });
    return NextResponse.json(
      {
        error: {
          code: "api_gateway_unreachable",
          message: "The backend API is temporarily unreachable.",
          recovery_suggestion: "Retry shortly or inspect the API deployment logs.",
        },
      },
      { status: 502 },
    );
  }
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/api/health") {
    return NextResponse.next();
  }
  if (!basicAuthAllowed(request)) {
    return unauthorized();
  }
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

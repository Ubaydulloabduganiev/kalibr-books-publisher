import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { proxy } from "./proxy";

const originalEnvironment = { ...process.env };

afterEach(() => {
  process.env = { ...originalEnvironment };
});

describe("application proxy", () => {
  it("leaves the platform health endpoint unlocalized and public", async () => {
    process.env = { ...process.env, NODE_ENV: "production" };
    delete process.env.ADMIN_BASIC_USERNAME;
    delete process.env.ADMIN_BASIC_PASSWORD;

    const response = await proxy(new NextRequest("http://localhost/api/health"));

    expect(response.status).toBe(200);
    expect(response.headers.get("x-middleware-next")).toBe("1");
    expect(response.headers.get("location")).toBeNull();
  });

  it("fails closed in production when administrator credentials are missing", async () => {
    process.env = { ...process.env, NODE_ENV: "production" };
    delete process.env.ADMIN_BASIC_USERNAME;
    delete process.env.ADMIN_BASIC_PASSWORD;

    const response = await proxy(new NextRequest("http://localhost/uz"));

    expect(response.status).toBe(401);
    expect(response.headers.get("www-authenticate")).toContain("Basic");
  });
});

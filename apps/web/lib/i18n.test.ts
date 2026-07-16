import { describe, expect, it } from "vitest";

import { getMessages, isLocale, localeLabel } from "./i18n";

describe("i18n", () => {
  it("recognizes only configured locales", () => {
    expect(isLocale("uz")).toBe(true);
    expect(isLocale("ru")).toBe(true);
    expect(isLocale("en")).toBe(false);
  });

  it("returns complete dictionaries", () => {
    expect(getMessages("uz").dashboard.title).toBeTruthy();
    expect(getMessages("ru").dashboard.title).toBeTruthy();
  });

  it("returns human-readable labels", () => {
    expect(localeLabel("uz")).toContain("O‘zbek");
    expect(localeLabel("ru")).toContain("Рус");
  });
});

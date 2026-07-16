"use client";

import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";

import { localeLabel, locales, type Locale } from "@/lib/i18n";

export function LocaleSwitcher({ locale, label }: { locale: Locale; label: string }) {
  const pathname = usePathname();
  const router = useRouter();

  function changeLocale(nextLocale: string) {
    if (!locales.includes(nextLocale as Locale)) return;
    const segments = pathname.split("/");
    segments[1] = nextLocale;
    const localizedPath = (segments.join("/") || `/${nextLocale}`) as Route;
    router.push(localizedPath);
  }

  return (
    <label className="sr-only" aria-label={label}>
      {label}
      <select
        value={locale}
        onChange={(event) => changeLocale(event.target.value)}
        className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/40"
      >
        {locales.map((item) => (
          <option key={item} value={item}>
            {localeLabel(item)}
          </option>
        ))}
      </select>
    </label>
  );
}

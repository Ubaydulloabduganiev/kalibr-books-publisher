import type { Metadata } from "next";
import { headers } from "next/headers";
import type { ReactNode } from "react";

import "./globals.css";

import { ThemeProvider } from "@/components/theme-provider";
import { defaultLocale, isLocale } from "@/lib/i18n";

export const metadata: Metadata = {
  title: {
    default: "Kalibr Publisher",
    template: "%s · Kalibr Publisher",
  },
  description: "Kalibr Books internal publishing platform",
  robots: { index: false, follow: false },
};

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const requestHeaders = await headers();
  const candidate = requestHeaders.get("x-kalibr-locale");
  const locale = candidate && isLocale(candidate) ? candidate : defaultLocale;

  return (
    <html lang={locale} suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}

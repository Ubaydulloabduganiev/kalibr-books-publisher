import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { getMessages, isLocale, locales } from "@/lib/i18n";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: Readonly<{ children: ReactNode; params: Promise<{ locale: string }> }>) {
  const { locale: candidate } = await params;
  if (!isLocale(candidate)) notFound();
  const messages = getMessages(candidate);

  return (
    <AppShell locale={candidate} messages={messages}>
      {children}
    </AppShell>
  );
}

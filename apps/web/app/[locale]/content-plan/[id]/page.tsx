import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ContentPlanDetail } from "@/components/content-plan-detail";
import { getMessages, isLocale } from "@/lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const messages = getMessages(locale);
  return { title: `${messages.contentPlan.title} — ${messages.brand.name}`, description: messages.contentPlan.description };
}

export default async function ContentPlanDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  if (!isLocale(locale)) notFound();
  const messages = getMessages(locale);
  return (
    <div className="space-y-6">
      <ContentPlanDetail id={id} locale={locale} messages={messages} />
    </div>
  );
}

import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ContentPlanUploader } from "@/components/content-plan-uploader";
import { ContentPlansList } from "@/components/content-plans-list";
import { getMessages, isLocale } from "@/lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const messages = getMessages(locale);
  return { title: `${messages.contentPlan.title} — ${messages.brand.name}`, description: messages.contentPlan.description };
}

export default async function ContentPlanPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const messages = getMessages(locale);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{messages.contentPlan.title}</h1>
        <p className="text-muted-foreground">{messages.contentPlan.description}</p>
      </div>
      <ContentPlanUploader messages={messages} />
      <ContentPlansList messages={messages} />
    </div>
  );
}

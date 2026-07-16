import { Activity, Clock3, Database, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { StatusCard } from "@/components/status-card";
import { ContentPlan } from "@/components/content-plan";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getSystemSnapshot } from "@/lib/api";
import { getMessages, isLocale } from "@/lib/i18n";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Dashboard" };

export default async function DashboardPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();

  const messages = getMessages(locale);
  const snapshot = await getSystemSnapshot();
  const passingChecks = snapshot.readiness
    ? Object.values(snapshot.readiness.checks).filter((check) => check.status === "pass").length
    : 0;
  const totalChecks = snapshot.readiness ? Object.keys(snapshot.readiness.checks).length : 0;

  const foundationItems = Object.values(messages.dashboard.items);

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
        <Badge tone="neutral">{messages.dashboard.eyebrow}</Badge>
        <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight sm:text-4xl">
          {messages.dashboard.title}
        </h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">{messages.dashboard.description}</p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard
          label={messages.dashboard.api}
          value={snapshot.connected ? messages.common.online : messages.common.offline}
          detail={snapshot.error ?? snapshot.readiness?.service}
          icon={Activity}
        />
        <StatusCard
          label={messages.dashboard.storage}
          value={`${passingChecks}/${totalChecks}`}
          detail={snapshot.connected ? messages.common.healthy : messages.common.degraded}
          icon={Database}
        />
        <StatusCard
          label={messages.dashboard.timezone}
          value={snapshot.meta?.timezone ?? "Asia/Tashkent"}
          icon={Clock3}
        />
        <StatusCard
          label={messages.dashboard.version}
          value={snapshot.meta?.version ?? "0.1.0"}
          icon={ShieldCheck}
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>{messages.dashboard.foundation}</CardTitle>
          <CardDescription>{messages.dashboard.foundationDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {foundationItems.map((item) => (
              <div key={item} className="flex items-start gap-3 rounded-lg border p-4">
                <span className="mt-1 size-2 rounded-full bg-success" aria-hidden="true" />
                <span className="text-sm font-medium">{item}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <ContentPlan messages={messages} />
    </div>
  );
}

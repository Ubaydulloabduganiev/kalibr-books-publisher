import { HardDrive, Server } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getSystemSnapshot } from "@/lib/api";
import { TelegramPublisher } from "@/components/telegram-publisher";
import { BulkScheduler } from "@/components/bulk-scheduler";
import { getMessages, isLocale } from "@/lib/i18n";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "System status" };

function formatBytes(value: number, locale: string): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  if (value <= 0) return "0 B";
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${new Intl.NumberFormat(locale).format(value / 1024 ** index)} ${units[index]}`;
}

export default async function SystemPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();

  const messages = getMessages(locale);
  const snapshot = await getSystemSnapshot();
  const intlLocale = locale === "uz" ? "uz-UZ" : "ru-RU";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{messages.system.title}</h1>
        <p className="mt-2 text-muted-foreground">{messages.system.description}</p>
      </div>

      {!snapshot.connected ? (
        <Card className="border-danger/40">
          <CardHeader>
            <CardTitle>{messages.system.unavailable}</CardTitle>
            <CardDescription>{messages.system.recovery}</CardDescription>
          </CardHeader>
          <CardContent>
            <code className="rounded bg-muted px-2 py-1 text-xs">{snapshot.error}</code>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="grid gap-5 pt-5 sm:grid-cols-3">
              <div className="flex gap-3">
                <Server className="size-5 text-primary" aria-hidden="true" />
                <div>
                  <p className="text-xs text-muted-foreground">{messages.system.service}</p>
                  <p className="mt-1 font-medium">{snapshot.readiness?.service}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{messages.system.environment}</p>
                <p className="mt-1 font-medium">{snapshot.meta?.environment}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{messages.system.checkedAt}</p>
                <p className="mt-1 font-medium">
                  {snapshot.readiness
                    ? new Intl.DateTimeFormat(intlLocale, {
                        dateStyle: "medium",
                        timeStyle: "medium",
                        timeZone: snapshot.meta?.timezone ?? "Asia/Tashkent",
                      }).format(new Date(snapshot.readiness.timestamp))
                    : "—"}
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            {Object.entries(snapshot.readiness?.checks ?? {}).map(([name, check]) => {
              const freeBytes = typeof check.details.free_bytes === "number" ? check.details.free_bytes : 0;
              return (
                <Card key={name}>
                  <CardHeader className="flex-row items-start justify-between gap-4">
                    <div>
                      <CardTitle className="capitalize">{name}</CardTitle>
                      <CardDescription>{messages.system.directory}</CardDescription>
                    </div>
                    <Badge tone={check.status === "pass" ? "success" : "danger"}>
                      {check.status === "pass" ? messages.common.healthy : messages.common.degraded}
                    </Badge>
                  </CardHeader>
                  <CardContent className="flex items-center gap-3">
                    <HardDrive className="size-5 text-primary" aria-hidden="true" />
                    <div>
                      <p className="text-xs text-muted-foreground">{messages.system.freeSpace}</p>
                      <p className="font-medium">{formatBytes(freeBytes, intlLocale)}</p>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <TelegramPublisher messages={messages} />
          <BulkScheduler messages={messages} />
        </>
      )}
    </div>
  );
}

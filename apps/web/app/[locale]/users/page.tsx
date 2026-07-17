import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { UserManager } from "@/components/user-manager";
import { getMessages, isLocale } from "@/lib/i18n";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Accounts" };

export default async function UsersPage({
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
        <h1 className="text-3xl font-semibold tracking-tight">{messages.users.title}</h1>
        <p className="mt-2 text-muted-foreground">{messages.users.description}</p>
      </div>
      <UserManager messages={messages} />
    </div>
  );
}

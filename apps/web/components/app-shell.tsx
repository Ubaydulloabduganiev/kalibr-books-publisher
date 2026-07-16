import { Activity, LayoutDashboard } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { LocaleSwitcher } from "@/components/locale-switcher";
import { MobileNavigation } from "@/components/mobile-navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import type { Locale, Messages } from "@/lib/i18n";

export function AppShell({
  children,
  locale,
  messages,
}: {
  children: ReactNode;
  locale: Locale;
  messages: Messages;
}) {
  const links = [
    { href: `/${locale}`, label: messages.nav.dashboard, icon: LayoutDashboard },
    { href: `/${locale}/system`, label: messages.nav.system, icon: Activity },
  ] as const;

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="hidden border-r bg-card/60 lg:flex lg:flex-col">
        <div className="border-b p-6">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-primary font-bold text-primary-foreground">
              K
            </div>
            <div>
              <p className="font-semibold leading-tight">{messages.brand.name}</p>
              <p className="text-xs text-muted-foreground">{messages.brand.subtitle}</p>
            </div>
          </div>
        </div>
        <nav className="grid gap-1 p-4">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t p-4 text-xs text-muted-foreground">
          Kalibr Books · 2026
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b bg-background/90 px-4 backdrop-blur lg:px-8">
          <div className="flex items-center gap-3">
            <MobileNavigation locale={locale} messages={messages} />
            <div className="lg:hidden">
              <p className="font-semibold leading-tight">{messages.brand.name}</p>
              <p className="text-xs text-muted-foreground">{messages.brand.subtitle}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LocaleSwitcher locale={locale} label={messages.common.language} />
            <ThemeToggle label={messages.common.theme} />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

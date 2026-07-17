"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import type { Locale, Messages } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function MobileNavigation({ locale, messages }: { locale: Locale; messages: Messages }) {
  const pathname = usePathname();
  const links = [
    { href: `/${locale}`, label: messages.nav.dashboard },
    { href: `/${locale}/system`, label: messages.nav.system },
    { href: `/${locale}/users`, label: messages.nav.users },
  ] as const;

  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <Button variant="ghost" size="icon" className="lg:hidden" aria-label={messages.common.menu}>
          <Menu aria-hidden="true" />
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 w-[min(88vw,320px)] border-r bg-background p-5 shadow-2xl outline-none">
          <div className="flex items-center justify-between">
            <div>
              <Dialog.Title className="font-semibold">{messages.brand.name}</Dialog.Title>
              <Dialog.Description className="text-xs text-muted-foreground">
                {messages.brand.subtitle}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close">
                <X aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </div>
          <nav className="mt-8 grid gap-2">
            {links.map((link) => {
              const active = pathname === link.href;
              return (
                <Dialog.Close asChild key={link.href}>
                  <Link
                    href={link.href}
                    className={cn(
                      "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      active ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                    )}
                  >
                    {link.label}
                  </Link>
                </Dialog.Close>
              );
            })}
          </nav>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

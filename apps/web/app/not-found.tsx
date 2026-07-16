import Link from "next/link";

import { Button } from "@/components/ui/button";
import { defaultLocale } from "@/lib/i18n";

export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <div className="max-w-md text-center">
        <p className="text-sm font-semibold text-primary">404</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Page not found</h1>
        <p className="mt-3 text-muted-foreground">
          The requested administration page does not exist.
        </p>
        <Button asChild className="mt-6">
          <Link href={`/${defaultLocale}`}>Open dashboard</Link>
        </Button>
      </div>
    </main>
  );
}

import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function StatusCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail?: string;
  icon: LucideIcon;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 pt-5">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
          {detail ? <p className="mt-1 text-xs text-muted-foreground">{detail}</p> : null}
        </div>
        <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
          <Icon className="size-5" aria-hidden="true" />
        </div>
      </CardContent>
    </Card>
  );
}

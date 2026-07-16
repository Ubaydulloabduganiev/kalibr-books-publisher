import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "success" | "danger" | "warning";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone };

const tones: Record<BadgeTone, string> = {
  neutral: "bg-muted text-foreground",
  success: "bg-success/15 text-success",
  danger: "bg-danger/15 text-danger",
  warning: "bg-warning/15 text-warning",
};

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", tones[tone], className)}
      {...props}
    />
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteContentPlan, listContentPlans, type ContentPlan } from "@/lib/api";

interface Messages {
  contentPlan: {
    plansTitle: string;
    plansEmpty: string;
    deletePlan: string;
    error: string;
    posts: string;
    created: string;
  };
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function ContentPlansList({ messages, locale }: { messages: Messages; locale: string }) {
  const t = messages.contentPlan;
  const [plans, setPlans] = useState<ContentPlan[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    const res = await listContentPlans();
    if (res.ok && res.data) {
      setPlans(res.data);
      setError(null);
    } else {
      setError(res.error ?? t.error);
    }
    setLoaded(true);
  }

  if (!loaded) {
    refresh();
  }

  async function handleDelete(plan: ContentPlan) {
    if (!confirm(`Delete plan "${plan.filename}" and its ${plan.post_count} post(s)?`)) return;
    setBusyId(plan.id);
    const res = await deleteContentPlan(plan.id);
    setBusyId(null);
    if (res.ok) {
      await refresh();
    } else {
      setError(res.error ?? t.error);
    }
  }

  if (!loaded) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.plansTitle}</CardTitle>
        <CardDescription>{t.posts}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <p className="text-sm text-danger">{error}</p>}
        {!error && plans.length === 0 && (
          <p className="text-sm text-muted-foreground">{t.plansEmpty}</p>
        )}
        {plans.map((plan) => (
          <div key={plan.id} className="rounded border p-3">
            <Link href={`/${locale}/content-plan/${plan.id}`} className="block">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{plan.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {t.created}: {formatDate(plan.created_at)} · {t.posts}: {plan.post_count}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={busyId === plan.id}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleDelete(plan);
                  }}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                  {t.deletePlan}
                </Button>
              </div>
              {plan.items.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                  {plan.items.slice(0, 5).map((item) => (
                    <li key={item.row}>
                      {item.row + 1}. {item.text.slice(0, 60)}
                      {item.text.length > 60 ? "…" : ""}
                    </li>
                  ))}
                  {plan.items.length > 5 && (
                    <li>… +{plan.items.length - 5} more</li>
                  )}
                </ul>
              )}
            </Link>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

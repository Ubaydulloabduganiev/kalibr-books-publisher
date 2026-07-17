"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteContentPlan, getContentPlan, type ContentPlan } from "@/lib/api";

interface Messages {
  contentPlan: {
    back: string;
    error: string;
    deletePlan: string;
    originalText: string;
    imagePrompt: string;
    schedule: string;
    caption: string;
    post: string;
    noCaption: string;
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

export function ContentPlanDetail({
  id,
  locale,
  messages,
}: {
  id: string;
  locale: string;
  messages: Messages;
}) {
  const t = messages.contentPlan;
  const [plan, setPlan] = useState<ContentPlan | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!loaded) {
    getContentPlan(id).then((res) => {
      if (res.ok && res.data) setPlan(res.data);
      else setError(res.error ?? t.error);
      setLoaded(true);
    });
  }

  async function handleDelete() {
    if (!plan) return;
    if (!confirm(`Delete plan "${plan.filename}" and its ${plan.post_count} post(s)?`)) return;
    setBusy(true);
    const res = await deleteContentPlan(plan.id);
    setBusy(false);
    if (res.ok) {
      window.location.href = `/${locale}/content-plan`;
    } else {
      setError(res.error ?? t.error);
    }
  }

  if (!loaded) return null;
  if (error && !plan) {
    return (
      <Card>
        <CardContent className="space-y-4 pt-6">
          <p className="text-sm text-danger">{error}</p>
          <Link href={`/${locale}/content-plan`} className="text-sm text-primary">
            ← {t.back}
          </Link>
        </CardContent>
      </Card>
    );
  }
  if (!plan) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Link href={`/${locale}/content-plan`} className="inline-flex items-center gap-1 text-sm text-primary">
          <ArrowLeft className="size-4" /> {t.back}
        </Link>
        <Button size="sm" variant="destructive" disabled={busy} onClick={handleDelete}>
          <Trash2 className="size-4" /> {t.deletePlan}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{plan.filename}</CardTitle>
          <CardDescription>
            {t.created}: {formatDate(plan.created_at)} · {t.posts}: {plan.post_count}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="px-2 py-2">#</th>
                  <th className="px-2 py-2">{t.originalText}</th>
                  <th className="px-2 py-2">{t.imagePrompt}</th>
                  <th className="px-2 py-2">{t.schedule}</th>
                  <th className="px-2 py-2">{t.caption}</th>
                  <th className="px-2 py-2">{t.post}</th>
                </tr>
              </thead>
              <tbody>
                {plan.items.map((item) => (
                  <tr key={item.row} className="border-b align-top">
                    <td className="px-2 py-2">{item.row + 1}</td>
                    <td className="px-2 py-2 whitespace-pre-wrap">{item.text}</td>
                    <td className="px-2 py-2 whitespace-pre-wrap">{item.image_prompt || "—"}</td>
                    <td className="px-2 py-2">{item.schedule}</td>
                    <td className="px-2 py-2 whitespace-pre-wrap">{item.caption || t.noCaption}</td>
                    <td className="px-2 py-2">
                      {item.post_id ? (
                        <Link href={`/${locale}`} className="text-primary">
                          {t.post}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

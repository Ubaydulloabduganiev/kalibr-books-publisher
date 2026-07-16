"use client";

import { useState } from "react";
import { Sparkles, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { automationPlanFile, automationPlanText } from "@/lib/api";
import type { Messages } from "@/lib/i18n";

type Props = { messages: Messages };

export function ContentPlan({ messages }: Props) {
  const t = messages.automation;
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [language, setLanguage] = useState<"uz" | "ru">("uz");
  const [stagger, setStagger] = useState(24);
  const [status, setStatus] = useState<"idle" | "working" | "ok" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [summary, setSummary] = useState<{ created: number; items: { title: string; run_at: string }[] } | null>(null);

  async function run(fileOrNull: File | null, rawText: string) {
    setStatus("working");
    setMessage(null);
    setSummary(null);
    const result =
      fileOrNull
        ? await automationPlanFile(fileOrNull, language, stagger)
        : await automationPlanText(rawText, language, stagger);
    if (result.ok && result.data) {
      setStatus("ok");
      setMessage(t.success);
      setSummary({ created: result.data.created, items: result.data.items });
    } else {
      setStatus("error");
      setMessage(result.error ?? t.error);
    }
  }

  async function handleFile(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    await run(file, "");
  }

  async function handleText(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    await run(null, text);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <form onSubmit={handleFile} className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <input
              id="plan-file"
              type="file"
              accept=".txt,.docx,.pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <label htmlFor="plan-file">
              <Button type="button" variant="outline" asChild>
                <span className="cursor-pointer">
                  <Upload className="mr-2 h-4 w-4" />
                  {t.upload}
                </span>
              </Button>
            </label>
            {file ? <span className="text-sm text-muted-foreground">{file.name}</span> : null}
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm">
              {t.language}
              <select
                className="ml-2 rounded border border-input bg-background px-2 py-1 text-sm"
                value={language}
                onChange={(e) => setLanguage(e.target.value as "uz" | "ru")}
              >
                <option value="uz">Oʻzbekcha</option>
                <option value="ru">Русский</option>
              </select>
            </label>
            <label className="text-sm">
              {t.stagger}
              <input
                type="number"
                min={1}
                max={168}
                className="ml-2 w-20 rounded border border-input bg-background px-2 py-1 text-sm"
                value={stagger}
                onChange={(e) => setStagger(Number(e.target.value))}
              />
            </label>
            <Button type="submit" disabled={status === "working" || !file}>
              <Sparkles className="mr-2 h-4 w-4" />
              {status === "working" ? t.generating : t.generate}
            </Button>
          </div>
        </form>

        <div className="text-center text-sm text-muted-foreground">{t.orText}</div>

        <form onSubmit={handleText} className="space-y-4">
          <textarea
            className="min-h-28 w-full rounded border border-input bg-background px-3 py-2 text-sm"
            placeholder={"- Topic one\n- Topic two"}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <Button type="submit" disabled={status === "working" || !text.trim()}>
            <Sparkles className="mr-2 h-4 w-4" />
            {status === "working" ? t.generating : t.generate}
          </Button>
        </form>

        {message ? (
          <p className={status === "error" ? "text-sm text-destructive" : "text-sm text-emerald-600"}>{message}</p>
        ) : null}

        {summary ? (
          <div className="rounded border p-3 text-sm">
            <p className="font-medium">
              {t.created}: {summary.created}
            </p>
            <ul className="mt-2 space-y-1">
              {summary.items.slice(0, 10).map((it) => (
                <li key={it.title} className="flex justify-between gap-3">
                  <span className="truncate">{it.title}</span>
                  <span className="shrink-0 text-muted-foreground">{it.run_at}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

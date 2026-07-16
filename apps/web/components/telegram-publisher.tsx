"use client";

import { useState } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { publishToTelegram } from "@/lib/api";
import type { Messages } from "@/lib/i18n";

type Props = { messages: Messages };

export function TelegramPublisher({ messages }: Props) {
  const t = messages.publisher;
  const [text, setText] = useState("");
  const [target, setTarget] = useState<"default" | "custom">("default");
  const [chatId, setChatId] = useState("");
  const [parseMode, setParseMode] = useState<"" | "Markdown" | "MarkdownV2" | "HTML">("");
  const [status, setStatus] = useState<"idle" | "sending" | "ok" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setStatus("sending");
    setMessage(null);
    const result = await publishToTelegram({
      text,
      target,
      chat_id: target === "custom" ? chatId : null,
      parse_mode: parseMode || null,
    });
    if (result.ok) {
      setStatus("ok");
      setMessage(t.success);
      setText("");
    } else {
      setStatus("error");
      setMessage(result.error ?? t.error);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="target"
                checked={target === "default"}
                onChange={() => setTarget("default")}
              />
              {t.defaultChannel}
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="target"
                checked={target === "custom"}
                onChange={() => setTarget("custom")}
              />
              {t.customChannel}
            </label>
          </div>

          {target === "custom" ? (
            <input
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
              placeholder={t.channel}
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
            />
          ) : null}

          <textarea
            className="min-h-32 w-full rounded border border-input bg-background px-3 py-2 text-sm"
            placeholder={t.messagePlaceholder}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <div className="flex items-center gap-3">
            <select
              className="rounded border border-input bg-background px-3 py-2 text-sm"
              value={parseMode}
              onChange={(e) => setParseMode(e.target.value as typeof parseMode)}
            >
              <option value="">{t.parseMode}: —</option>
              <option value="Markdown">Markdown</option>
              <option value="MarkdownV2">MarkdownV2</option>
              <option value="HTML">HTML</option>
            </select>

            <Button type="submit" disabled={status === "sending" || !text.trim()}>
              <Send className="mr-2 size-4" aria-hidden="true" />
              {status === "sending" ? t.sending : t.send}
            </Button>
          </div>

          {status === "ok" && message ? (
            <p className="text-sm text-emerald-600">{message}</p>
          ) : null}
          {status === "error" && message ? (
            <p className="text-sm text-danger">{t.error}: {message}</p>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}

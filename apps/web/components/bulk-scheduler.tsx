"use client";

import { useEffect, useState } from "react";
import { Calendar, Image as ImageIcon, Send, Trash2, Upload } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  createPost,
  deletePost,
  listPosts,
  schedulePost,
  uploadMedia,
  type MediaItem,
  type PostOut,
  type ScheduleInput,
} from "@/lib/api";
import type { Messages } from "@/lib/i18n";

type Props = { messages: Messages };

interface DraftPost {
  id: string;
  text: string;
  media: MediaItem[];
  target: "default" | "custom";
  chatId: string;
  mode: "once" | "recurring";
  runAt: string;
  everyHours: string;
}

function blankDraft(): DraftPost {
  return {
    id: crypto.randomUUID(),
    text: "",
    media: [],
    target: "default",
    chatId: "",
    mode: "once",
    runAt: "",
    everyHours: "24",
  };
}

export function BulkScheduler({ messages }: Props) {
  const t = messages.scheduler;
  const [drafts, setDrafts] = useState<DraftPost[]>([blankDraft()]);
  const [queue, setQueue] = useState<PostOut[]>([]);
  const [status, setStatus] = useState<"idle" | "saving" | "ok" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);

  async function refresh() {
    const res = await listPosts();
    if (res.ok && res.data) setQueue(res.data.posts);
  }

  useEffect(() => {
    refresh();
  }, []);

  function update(id: string, patch: Partial<DraftPost>) {
    setDrafts((prev) => prev.map((d) => (d.id === id ? { ...d, ...patch } : d)));
  }

  async function handleUpload(id: string, file: File) {
    setUploading(id);
    const res = await uploadMedia(file);
    setUploading(null);
    if (!res.ok || !res.data) {
      setMessage(res.error ?? t.uploadError);
      setStatus("error");
      return;
    }
    update(id, {
      media: [...drafts.find((d) => d.id === id)!.media, { kind: res.data.kind as "photo" | "video", path: res.data.path }],
    });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const valid = drafts.filter((d) => d.text.trim().length > 0);
    if (valid.length === 0) return;
    setStatus("saving");
    setMessage(null);
    let created = 0;
    for (const d of valid) {
      const schedule: ScheduleInput =
        d.mode === "recurring"
          ? { mode: "recurring", every_hours: Number(d.everyHours) || 24 }
          : { mode: "once", run_at: d.runAt ? new Date(d.runAt).toISOString() : null };
      const res = await createPost({
        text: d.text,
        media: d.media,
        target: d.target === "custom" ? d.chatId : null,
        schedule,
      });
      if (res.ok) created += 1;
    }
    if (created > 0) {
      setStatus("ok");
      setMessage(`${t.success} (${created})`);
      setDrafts([blankDraft()]);
      await refresh();
    } else {
      setStatus("error");
      setMessage(t.error);
    }
  }

  async function handleDelete(id: string) {
    await deletePost(id);
    await refresh();
  }

  async function handleNow(id: string) {
    await schedulePost(id, { mode: "once", run_at: null });
    await refresh();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {drafts.map((d, idx) => (
            <div key={d.id} className="rounded-lg border border-input p-4 space-y-3">
              <div className="flex items-center justify-between">
                <Badge tone="neutral">#{idx + 1}</Badge>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setDrafts((prev) => prev.filter((x) => x.id !== d.id))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              <textarea
                className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                rows={3}
                placeholder={t.messagePlaceholder}
                value={d.text}
                onChange={(e) => update(d.id, { text: e.target.value })}
              />
              <div className="flex flex-wrap gap-2 items-center">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <Upload className="h-4 w-4" />
                  <input
                    type="file"
                    accept="image/*,video/*"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleUpload(d.id, f);
                    }}
                  />
                  <span>{uploading === d.id ? t.uploading : t.addMedia}</span>
                </label>
                {d.media.map((m, i) => (
                  <Badge key={i} tone="neutral">
                    <ImageIcon className="h-3 w-3 mr-1" />
                    {m.kind}
                  </Badge>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <select
                  className="rounded border border-input bg-background px-3 py-2 text-sm"
                  value={d.target}
                  onChange={(e) => update(d.id, { target: e.target.value as "default" | "custom" })}
                >
                  <option value="default">{t.defaultChannel}</option>
                  <option value="custom">{t.customChannel}</option>
                </select>
                {d.target === "custom" ? (
                  <input
                    className="rounded border border-input bg-background px-3 py-2 text-sm"
                    placeholder={t.channel}
                    value={d.chatId}
                    onChange={(e) => update(d.id, { chatId: e.target.value })}
                  />
                ) : (
                  <div />
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <select
                  className="rounded border border-input bg-background px-3 py-2 text-sm"
                  value={d.mode}
                  onChange={(e) => update(d.id, { mode: e.target.value as "once" | "recurring" })}
                >
                  <option value="once">{t.once}</option>
                  <option value="recurring">{t.recurring}</option>
                </select>
                {d.mode === "once" ? (
                  <input
                    type="datetime-local"
                    className="rounded border border-input bg-background px-3 py-2 text-sm"
                    value={d.runAt}
                    onChange={(e) => update(d.id, { runAt: e.target.value })}
                  />
                ) : (
                  <input
                    type="number"
                    min={1}
                    className="rounded border border-input bg-background px-3 py-2 text-sm"
                    placeholder={t.everyHours}
                    value={d.everyHours}
                    onChange={(e) => update(d.id, { everyHours: e.target.value })}
                  />
                )}
              </div>
            </div>
          ))}

          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => setDrafts((p) => [...p, blankDraft()])}>
              + {t.addPost}
            </Button>
            <Button type="submit" disabled={status === "saving"}>
              <Send className="h-4 w-4 mr-1" />
              {status === "saving" ? t.saving : t.scheduleAll}
            </Button>
          </div>

          {message ? (
            <p className={status === "error" ? "text-sm text-red-500" : "text-sm text-green-600"}>{message}</p>
          ) : null}
        </form>

        <div className="mt-8">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Calendar className="h-4 w-4" /> {t.queue}
          </h3>
          {queue.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t.queueEmpty}</p>
          ) : (
            <ul className="space-y-2">
              {queue.map((p) => (
                <li key={p.id} className="flex items-center justify-between rounded border border-input px-3 py-2 text-sm">
                  <div className="truncate max-w-[60%]">
                    <span className="font-medium">{p.status}</span> · {p.text.slice(0, 40)}
                    {p.media.length > 0 ? ` (+${p.media.length} media)` : ""}
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => handleNow(p.id)}>
                      {t.sendNow}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(p.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

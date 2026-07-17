"use client";

import { useEffect, useState } from "react";
import { Calendar, Image as ImageIcon, Send, Trash2, Upload } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  createPostsBulk,
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
    let active = true;
    void listPosts().then((result) => {
      if (active && result.ok && result.data) setQueue(result.data.posts);
    });
    return () => {
      active = false;
    };
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
    const uploadedMedia: MediaItem = {
      kind: res.data.kind as MediaItem["kind"],
      path: res.data.path,
    };
    setDrafts((previous) =>
      previous.map((draft) =>
        draft.id === id ? { ...draft, media: [...draft.media, uploadedMedia] } : draft,
      ),
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const valid = drafts.filter((d) => d.text.trim().length > 0);
    if (valid.length === 0) return;
    if (valid.some((draft) => !draft.runAt)) {
      setStatus("error");
      setMessage(t.scheduleRequired);
      return;
    }
    setStatus("saving");
    setMessage(null);
    const posts = valid.map((draft) => {
      const schedule: ScheduleInput =
        draft.mode === "recurring"
          ? {
              mode: "recurring",
              run_at: new Date(draft.runAt).toISOString(),
              every_hours: Number(draft.everyHours) || 24,
            }
          : { mode: "once", run_at: new Date(draft.runAt).toISOString() };
      return {
        text: draft.text,
        media: draft.media,
        target: draft.target === "custom" ? draft.chatId : null,
        schedule,
      };
    });
    const result = await createPostsBulk(posts);
    if (result.ok && result.data) {
      setStatus("ok");
      setMessage(`${t.success} (${result.data.created})`);
      setDrafts([blankDraft()]);
      await refresh();
    } else {
      setStatus("error");
      setMessage(result.error ?? t.error);
    }
  }

  async function handleDelete(id: string) {
    const result = await deletePost(id);
    if (!result.ok) {
      setStatus("error");
      setMessage(result.error ?? t.error);
      return;
    }
    setMessage(null);
    await refresh();
  }

  async function handleNow(post: PostOut) {
    if (post.status === "delivery_uncertain" && !window.confirm(t.uncertainConfirmation)) {
      return;
    }
    const result = await schedulePost(post.id, {
      mode: "once",
      run_at: new Date().toISOString(),
    });
    if (!result.ok) {
      setStatus("error");
      setMessage(result.error ?? t.error);
      return;
    }
    setMessage(null);
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
                    accept="image/*,video/*,.pdf,.doc,.docx"
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
                  <div className="grid gap-2">
                    <input
                      type="datetime-local"
                      className="rounded border border-input bg-background px-3 py-2 text-sm"
                      value={d.runAt}
                      onChange={(e) => update(d.id, { runAt: e.target.value })}
                    />
                    <input
                      type="number"
                      min={1}
                      className="rounded border border-input bg-background px-3 py-2 text-sm"
                      placeholder={t.everyHours}
                      value={d.everyHours}
                      onChange={(e) => update(d.id, { everyHours: e.target.value })}
                    />
                  </div>
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
                    {p.status !== "sent" && p.status !== "publishing" ? (
                      <Button size="sm" variant="ghost" onClick={() => handleNow(p)}>
                        {t.sendNow}
                      </Button>
                    ) : null}
                    {p.status !== "sent" &&
                    p.status !== "publishing" &&
                    p.status !== "delivery_uncertain" ? (
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(p.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    ) : null}
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

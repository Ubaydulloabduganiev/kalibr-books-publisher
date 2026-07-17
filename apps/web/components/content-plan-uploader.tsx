"use client";

import { useRef, useState } from "react";
import { FileUp, Loader2, UploadCloud } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  previewContentPlan,
  uploadContentPlan,
  type ContentPlanPreviewItem,
} from "@/lib/api";

interface Messages {
  contentPlan: {
    title: string;
    description: string;
    dropCsv: string;
    chooseFile: string;
    preview: string;
    generateSchedule: string;
    previewing: string;
    generating: string;
    row: string;
    text: string;
    imagePrompt: string;
    schedule: string;
    createdCount: string;
    previewEmpty: string;
    error: string;
    sample: string;
    sampleCaption: string;
  };
}

export function ContentPlanUploader({ messages }: { messages: Messages }) {
  const t = messages.contentPlan;
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ContentPlanPreviewItem[]>([]);
  const [busy, setBusy] = useState<"preview" | "upload" | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handlePreview() {
    if (!file) return;
    setBusy("preview");
    setError(null);
    const res = await previewContentPlan(file);
    setBusy(null);
    if (!res.ok) {
      setError(res.error ?? t.error);
      setPreview([]);
      return;
    }
    setPreview(res.data?.items ?? []);
  }

  async function handleUpload() {
    if (!file) return;
    setBusy("upload");
    setError(null);
    setResult(null);
    const res = await uploadContentPlan(file);
    setBusy(null);
    if (!res.ok) {
      setError(res.error ?? t.error);
      return;
    }
    setResult(`${t.createdCount.replace("{n}", String(res.data?.count ?? 0))}`);
    setPreview([]);
    setFile(null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-dashed p-6 text-center">
          <UploadCloud className="mx-auto mb-2 size-8 text-muted-foreground" />
          <p className="mb-3 text-sm text-muted-foreground">{t.dropCsv}</p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <Button variant="outline" onClick={() => inputRef.current?.click()}>
            <FileUp className="mr-2 size-4" />
            {t.chooseFile}
          </Button>
          {file && <p className="mt-2 text-sm">{file.name}</p>}
        </div>

        <div className="flex gap-2">
          <Button onClick={handlePreview} disabled={!file || busy !== null}>
            {busy === "preview" ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
            {t.preview}
          </Button>
          <Button onClick={handleUpload} disabled={!file || busy !== null}>
            {busy === "upload" ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
            {t.generateSchedule}
          </Button>
        </div>

        {error && (
          <p className="rounded bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
        )}
        {result && (
          <p className="rounded bg-primary/10 px-3 py-2 text-sm text-primary">{result}</p>
        )}

        {preview.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">{t.preview}</p>
            <div className="max-h-72 space-y-2 overflow-auto">
              {preview.map((item) => (
                <div key={item.row} className="rounded border p-2 text-xs">
                  <p className="font-medium">
                    {t.row} {item.row + 1}
                  </p>
                  <p>
                    <span className="text-muted-foreground">{t.text}:</span> {item.text}
                  </p>
                  <p>
                    <span className="text-muted-foreground">{t.imagePrompt}:</span> {item.image_prompt}
                  </p>
                  <p>
                    <span className="text-muted-foreground">{t.schedule}:</span> {item.schedule}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded bg-muted p-3 text-xs text-muted-foreground">
          <p className="mb-1 font-medium">{t.sample}:</p>
          <pre className="whitespace-pre-wrap">{`text,image_prompt,schedule
${t.sampleCaption},a cozy bookshelf with English grammar books,2026-07-20T09:00:00+05:00
Daily vocabulary tip,a flat-lay of vocabulary flashcards,EVERY 24h`}</pre>
        </div>
      </CardContent>
    </Card>
  );
}

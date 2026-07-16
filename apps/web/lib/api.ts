export type ReadinessCheck = {
  status: "pass" | "fail";
  details: Record<string, string | number>;
};

export type ReadinessResponse = {
  status: "ok" | "degraded";
  service: string;
  version: string;
  timestamp: string;
  checks: Record<string, ReadinessCheck>;
};

export type MetaResponse = {
  name: string;
  version: string;
  environment: string;
  timezone: string;
  default_locale: string;
  supported_locales: string[];
};

export type SystemSnapshot = {
  connected: boolean;
  readiness: ReadinessResponse | null;
  meta: MetaResponse | null;
  error: string | null;
};


export type PublishTarget = "default" | "custom";

export type TelegramPublishRequest = {
  text: string;
  target: PublishTarget;
  chat_id?: string | null;
  parse_mode?: "Markdown" | "MarkdownV2" | "HTML" | null;
  disable_web_page_preview?: boolean;
};

export type TelegramPublishResponse = {
  ok: boolean;
  chat_id: string;
  message_id: number | null;
};

export type PublishResult = {
  ok: boolean;
  data: TelegramPublishResponse | null;
  error: string | null;
};

const apiBaseUrl =
  typeof window === "undefined"
    ? process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000"
    : "";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`API returned HTTP ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getSystemSnapshot(): Promise<SystemSnapshot> {
  try {
    const [readiness, meta] = await Promise.all([
      fetchJson<ReadinessResponse>("/api/v1/health/ready"),
      fetchJson<MetaResponse>("/api/v1/meta"),
    ]);
    return { connected: true, readiness, meta, error: null };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { connected: false, readiness: null, meta: null, error: message };
  }
}

export async function publishToTelegram(
  payload: TelegramPublishRequest,
): Promise<PublishResult> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/telegram/publish`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return {
        ok: false,
        data: null,
        error: detail?.error?.message ?? `API returned HTTP ${response.status}`,
      };
    }
    const data = (await response.json()) as TelegramPublishResponse;
    return { ok: true, data, error: null };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, data: null, error: message };
  }
}


// --- Bulk posts + media + scheduling ---

export type ScheduleMode = "once" | "recurring";

export interface MediaItem {
  kind: "photo" | "video";
  path: string;
}

export interface ScheduleInput {
  mode?: ScheduleMode;
  run_at?: string | null;
  every_hours?: number | null;
  end_at?: string | null;
}

export interface AiConfigInput {
  rewrite?: boolean;
  language?: string;
  choose_order?: boolean;
  choose_time?: boolean;
}

export interface PostInput {
  text: string;
  media?: MediaItem[];
  target?: string | null;
  schedule?: ScheduleInput;
  ai?: AiConfigInput;
}

export interface PostOut {
  id: string;
  text: string;
  media: MediaItem[];
  target: string | null;
  parse_mode: string | null;
  schedule: ScheduleInput & { next_run?: string | null };
  ai: AiConfigInput;
  status: string;
  created_at: string;
  sent_at: string | null;
  last_error: string | null;
  send_count: number;
}

export interface UploadResult {
  ok: boolean;
  data?: { path: string; kind: string; size: number };
  error?: string;
}

export interface CreateResult {
  ok: boolean;
  data?: PostOut;
  error?: string;
}

export interface ListResult {
  ok: boolean;
  data?: { count: number; posts: PostOut[] };
  error?: string;
}

export async function uploadMedia(file: File): Promise<UploadResult> {
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${apiBaseUrl}/api/v1/posts/upload`, {
      method: "POST",
      cache: "no-store",
      body: form,
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return { ok: false, error: detail?.error?.message ?? "Upload failed" };
    }
    const data = (await response.json()) as { path: string; kind: string; size: number };
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, error: message };
  }
}

export async function createPost(payload: PostInput): Promise<CreateResult> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return { ok: false, error: detail?.error?.message ?? "Create failed" };
    }
    const data = (await response.json()) as PostOut;
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, error: message };
  }
}

export async function listPosts(): Promise<ListResult> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts`, {
      method: "GET",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return { ok: false, error: detail?.error?.message ?? "List failed" };
    }
    const data = (await response.json()) as { count: number; posts: PostOut[] };
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, error: message };
  }
}

export async function schedulePost(
  id: string,
  schedule: ScheduleInput,
): Promise<CreateResult> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts/${id}/schedule`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(schedule),
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return { ok: false, error: detail?.error?.message ?? "Schedule failed" };
    }
    const data = (await response.json()) as PostOut;
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, error: message };
  }
}

export async function deletePost(id: string): Promise<{ ok: boolean; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts/${id}`, {
      method: "DELETE",
      cache: "no-store",
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return { ok: false, error: detail?.error?.message ?? "Delete failed" };
    }
    return { ok: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, error: message };
  }
}


export interface AutomationItem {
  id: string;
  title: string;
  run_at: string;
  image: string;
  text: string;
}

export interface AutomationResult {
  source: string;
  created: number;
  items: AutomationItem[];
}

export async function automationPlanFile(
  file: File,
  language: string,
  staggerHours: number,
): Promise<{ ok: boolean; data: AutomationResult | null; error?: string }> {
  try {
    const body = new FormData();
    body.append("file", file);
    body.append("language", language);
    body.append("stagger_hours", String(staggerHours));
    const response = await fetch(`${apiBaseUrl}/api/v1/automation/plan-file`, {
      method: "POST",
      cache: "no-store",
      body,
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return { ok: false, data: null, error: detail?.error?.message ?? `API returned HTTP ${response.status}` };
    }
    const data = (await response.json()) as AutomationResult;
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, data: null, error: message };
  }
}

export async function automationPlanText(
  text: string,
  language: string,
  staggerHours: number,
): Promise<{ ok: boolean; data: AutomationResult | null; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/automation/plan-text`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ text, language, stagger_hours: staggerHours }),
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null)) as
        | { error?: { message?: string } }
        | null;
      return { ok: false, data: null, error: detail?.error?.message ?? `API returned HTTP ${response.status}` };
    }
    const data = (await response.json()) as AutomationResult;
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown API error";
    return { ok: false, data: null, error: message };
  }
}

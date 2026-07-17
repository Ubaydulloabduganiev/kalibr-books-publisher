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
  disable_notification?: boolean;
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

export type ScheduleMode = "once" | "recurring";

export interface MediaItem {
  kind: "photo" | "video" | "animation" | "document";
  path: string;
}

export interface ScheduleInput {
  mode?: ScheduleMode;
  run_at?: string | null;
  every_hours?: number | null;
  end_at?: string | null;
}

export interface PostOut {
  id: string;
  text: string;
  media: MediaItem[];
  target: string | null;
  parse_mode: string | null;
  schedule: ScheduleInput & { next_run?: string | null };
  status: string;
  created_at: string;
  sent_at: string | null;
  last_error: string | null;
  send_count: number;
}

export interface PostInput {
  text: string;
  media?: MediaItem[];
  target?: string | null;
  parse_mode?: "Markdown" | "MarkdownV2" | "HTML" | null;
  schedule: ScheduleInput;
}

function normalizeServerApiUrl(value: string | undefined): string {
  const normalized = value?.trim().replace(/\/+$/, "");
  if (!normalized) return "http://127.0.0.1:8000";
  if (/^https?:\/\//i.test(normalized)) return normalized;
  return `http://${normalized}`;
}

const apiBaseUrl =
  typeof window === "undefined" ? normalizeServerApiUrl(process.env.API_INTERNAL_URL) : "";

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = (await response.json().catch(() => null)) as
    | { error?: { message?: string }; detail?: string }
    | null;
  return payload?.error?.message ?? payload?.detail ?? fallback;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, `API returned HTTP ${response.status}`));
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
      return {
        ok: false,
        data: null,
        error: await readApiError(response, `API returned HTTP ${response.status}`),
      };
    }
    return { ok: true, data: (await response.json()) as TelegramPublishResponse, error: null };
  } catch (error) {
    return {
      ok: false,
      data: null,
      error: error instanceof Error ? error.message : "Unknown API error",
    };
  }
}

export async function uploadMedia(
  file: File,
): Promise<{ ok: boolean; data?: { path: string; kind: string; size: number }; error?: string }> {
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${apiBaseUrl}/api/v1/posts/upload`, {
      method: "POST",
      cache: "no-store",
      body: form,
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Upload failed") };
    }
    return {
      ok: true,
      data: (await response.json()) as { path: string; kind: string; size: number },
    };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function createPost(
  payload: PostInput,
): Promise<{ ok: boolean; data?: PostOut; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Create failed") };
    }
    return { ok: true, data: (await response.json()) as PostOut };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function createPostsBulk(
  posts: PostInput[],
): Promise<{ ok: boolean; data?: { created: number; ids: string[] }; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts/bulk`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ posts }),
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Bulk create failed") };
    }
    return {
      ok: true,
      data: (await response.json()) as { created: number; ids: string[] },
    };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function listPosts(): Promise<{
  ok: boolean;
  data?: { count: number; posts: PostOut[] };
  error?: string;
}> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "List failed") };
    }
    return {
      ok: true,
      data: (await response.json()) as { count: number; posts: PostOut[] },
    };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function schedulePost(
  id: string,
  schedule: ScheduleInput,
): Promise<{ ok: boolean; data?: PostOut; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts/${encodeURIComponent(id)}/schedule`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(schedule),
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Schedule failed") };
    }
    return { ok: true, data: (await response.json()) as PostOut };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export interface UserOut {
  id: string;
  username: string;
  display_name: string;
  role: "admin" | "editor";
  created_at: string;
  updated_at: string;
}

export interface UserList {
  count: number;
  users: UserOut[];
}

export async function listUsers(): Promise<{ ok: boolean; data?: UserList; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/users`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "List failed") };
    }
    return { ok: true, data: (await response.json()) as UserList };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function createUser(payload: {
  username: string;
  password: string;
  display_name?: string;
  role: "admin" | "editor";
}): Promise<{ ok: boolean; data?: UserOut; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/users`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Create failed") };
    }
    return { ok: true, data: (await response.json()) as UserOut };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function changeUserPassword(
  id: string,
  new_password: string,
): Promise<{ ok: boolean; data?: UserOut; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/users/${encodeURIComponent(id)}/password`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ new_password }),
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Password change failed") };
    }
    return { ok: true, data: (await response.json()) as UserOut };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function deleteUser(id: string): Promise<{ ok: boolean; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/users/${encodeURIComponent(id)}`, {
      method: "DELETE",
      cache: "no-store",
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Delete failed") };
    }
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function deletePost(id: string): Promise<{ ok: boolean; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/posts/${encodeURIComponent(id)}`, {
      method: "DELETE",
      cache: "no-store",
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Delete failed") };
    }
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export interface ContentPlanPreviewItem {
  row: number;
  text: string;
  image_prompt: string;
  schedule: string;
}

export interface ContentPlanPreview {
  count: number;
  items: ContentPlanPreviewItem[];
}

export async function previewContentPlan(
  file: File,
): Promise<{ ok: boolean; data?: ContentPlanPreview; error?: string }> {
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${apiBaseUrl}/api/v1/content-plan/preview`, {
      method: "POST",
      cache: "no-store",
      body: form,
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Preview failed") };
    }
    return { ok: true, data: (await response.json()) as ContentPlanPreview };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

export async function uploadContentPlan(
  file: File,
): Promise<{ ok: boolean; data?: { count: number; items: unknown[] }; error?: string }> {
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${apiBaseUrl}/api/v1/content-plan/upload`, {
      method: "POST",
      cache: "no-store",
      body: form,
    });
    if (!response.ok) {
      return { ok: false, error: await readApiError(response, "Upload failed") };
    }
    return { ok: true, data: (await response.json()) as { count: number; items: unknown[] } };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown API error" };
  }
}

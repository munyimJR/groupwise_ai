/** Thin fetch wrapper for the GroupWise API (proxied at /api by Next.js rewrites). */

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type TokenGetter = () => Promise<string | null>;
let getToken: TokenGetter = async () => null;
let onUnauthorized: (() => void) | null = null;

export function configureApi(tokenGetter: TokenGetter, unauthorized: () => void) {
  getToken = tokenGetter;
  onUnauthorized = unauthorized;
}

function messageFrom(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors → short, human messages
    const first = detail[0] as { msg?: string; loc?: (string | number)[] };
    const field = String(first.loc?.slice(-1)[0] ?? "").replace(/_/g, " ");
    const msg = (first.msg ?? "").replace(/^Value error, /, "");
    if (/valid email/i.test(msg)) return "Please enter a valid email address.";
    if (/at least \d+ character/i.test(msg) && field) return `${field[0].toUpperCase()}${field.slice(1)} is too short.`;
    return field ? `${field[0].toUpperCase()}${field.slice(1)}: ${msg.charAt(0).toLowerCase()}${msg.slice(1)}` : msg || fallback;
  }
  return fallback;
}

export async function api<T>(path: string, init: { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (init.auth !== false) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method: init.method ?? (init.body !== undefined ? "POST" : "GET"),
      headers,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: init.signal,
      cache: "no-store",
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(0, "Can't reach GroupWise right now. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    const fallback = res.status >= 500 ? "Something went wrong on our side. Please try again." : "Request failed.";
    if (res.status === 401 && init.auth !== false) onUnauthorized?.();
    throw new ApiError(res.status, messageFrom(detail, fallback));
  }
  return data as T;
}

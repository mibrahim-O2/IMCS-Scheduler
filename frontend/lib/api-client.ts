/**
 * Typed fetch wrapper for the FastAPI backend (docs/PROJECT_ARCHITECTURE.md §5).
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function errorMessage(cause: unknown): string {
  // Turns whatever was thrown into text that can be shown to the user.
  return cause instanceof Error ? cause.message : String(cause);
}

async function readErrorMessage(response: Response): Promise<string> {
  // FastAPI returns the reason in `detail`, which is a string for our own errors
  // and a list of field errors when validation fails.
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // Validation errors carry a `loc` path; naming the field makes the message actionable.
      return detail
        .map((item) => {
          const field = Array.isArray(item?.loc) ? item.loc.slice(1).join(".") : "";
          return field ? `${field}: ${item?.msg}` : (item?.msg ?? JSON.stringify(item));
        })
        .join("; ");
    }
  } catch {
    // Body was not JSON — fall through to the status-code message.
  }
  return `The server answered with status ${response.status}.`;
}

async function send<T>(path: string, init: RequestInit): Promise<T> {
  // Shared request path: a dropped connection and a non-2xx answer both become readable errors.
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error(`Can't reach the server at ${API_BASE_URL}. Check that the backend is running, then try again.`);
  }
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as T;
}

export function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  // JSON request that asks for JSON back.
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  return send<T>(path, { ...init, headers });
}

export function apiUpload<T>(path: string, form: FormData): Promise<T> {
  // Multipart request for file uploads; the browser sets the boundary header itself.
  return send<T>(path, { method: "POST", body: form });
}

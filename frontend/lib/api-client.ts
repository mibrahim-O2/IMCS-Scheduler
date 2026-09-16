/**
 * Typed fetch wrapper for the FastAPI backend (docs/PROJECT_ARCHITECTURE.md §5).
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  return `Request failed with status ${response.status}`;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  // Plain JSON request; throws with the backend's own message so the UI can show it.
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as T;
}

export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  // Multipart request for file uploads; the browser sets the boundary header itself.
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return (await response.json()) as T;
}

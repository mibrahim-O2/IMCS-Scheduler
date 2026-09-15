/**
 * Typed fetch wrapper for the FastAPI backend (docs/PROJECT_ARCHITECTURE.md §5).
 * Phase 0 placeholder: no backend endpoints are called yet.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

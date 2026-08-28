"use client";

import type {
  AssistantAnswer,
  CertificationScheme,
  CompareResponse,
  ComplianceChecklist,
  HallmarkingTopic,
  Laboratory,
  Language,
  Meta,
  Standard,
} from "./types";

const BASE = "/api/backend/api";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("bis_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body; keep the status message */
    }
    throw new ApiError(detail, res.status);
  }

  return res.json() as Promise<T>;
}

const post = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

// --------------------------------------------------------------------------
// System
// --------------------------------------------------------------------------
export const getMeta = () => request<Meta>("/meta");

// --------------------------------------------------------------------------
// Assistant
// --------------------------------------------------------------------------
export const chat = (message: string, language: Language = "en") =>
  post<AssistantAnswer>("/chat", { message, language });

export type StageEvent = { event: string; data: Record<string, unknown> };

/**
 * Consume the SSE pipeline. `onStage` fires for each retrieval stage; the promise
 * resolves with the final answer. Falls back to the non-streaming endpoint if the
 * stream cannot be opened, so the UI never dead-ends on a proxy hiccup.
 */
export async function chatStream(
  message: string,
  language: Language,
  onStage: (stage: StageEvent) => void,
  signal?: AbortSignal,
): Promise<AssistantAnswer> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, language }),
    signal,
  });

  if (!res.ok || !res.body) return chat(message, language);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer: AssistantAnswer | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const eventLine = frame.split("\n").find((l) => l.startsWith("event: "));
      const dataLine = frame.split("\n").find((l) => l.startsWith("data: "));
      if (!eventLine || !dataLine) continue;

      const event = eventLine.slice(7).trim();
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataLine.slice(6));
      } catch {
        continue;
      }

      if (event === "answer") answer = data as unknown as AssistantAnswer;
      else if (event === "error") throw new ApiError(String(data.message), 500);
      else onStage({ event, data });
    }
  }

  if (!answer) throw new ApiError("The assistant did not return an answer.", 500);
  return answer;
}

// --------------------------------------------------------------------------
// Standards
// --------------------------------------------------------------------------
export const searchStandards = (body: {
  query?: string;
  status?: string | null;
  industry?: string | null;
  category?: string | null;
  year_from?: number | null;
  year_to?: number | null;
  limit?: number;
}) => post<Standard[]>("/standards/search", body);

export const standardFacets = () =>
  request<{ statuses: string[]; industries: string[]; categories: string[]; years: string[] }>(
    "/standards/facets",
  );

export const recommendStandards = (description: string, language: Language = "en", limit = 5) =>
  post<AssistantAnswer>("/standards/recommend", { description, language, limit });

export const compareStandards = (standard_numbers: string[]) =>
  post<CompareResponse>("/standards/compare", { standard_numbers });

export const getStandard = (number: string) =>
  request<Standard>(`/standards/${encodeURIComponent(number)}`);

export const getStandardEvidence = (number: string) =>
  request<{ standard: Standard; passages: unknown[]; demo: boolean }>(
    `/standards/${encodeURIComponent(number)}/evidence`,
  );

// --------------------------------------------------------------------------
// Services
// --------------------------------------------------------------------------
export const analyzeCertification = (body: {
  product?: string;
  standard_number?: string;
  language?: Language;
}) => post<AssistantAnswer>("/certification/analyze", body);

export const listSchemes = () => request<CertificationScheme[]>("/certification/schemes");

export const searchLabs = (body: {
  query?: string;
  product_category?: string | null;
  standard_number?: string | null;
  test_type?: string | null;
  state?: string | null;
  city?: string | null;
  limit?: number;
}) => post<Laboratory[]>("/labs/search", body);

export const labFacets = () =>
  request<{
    states: string[];
    cities: string[];
    categories: string[];
    test_types: string[];
    standards: string[];
  }>("/labs/facets");

export const hallmarkingQuery = (query: string, language: Language = "en") =>
  post<AssistantAnswer>("/hallmarking/query", { query, language });

export const hallmarkingTopics = () => request<HallmarkingTopic[]>("/hallmarking/topics");

export const consumerQuery = (query: string, language: Language = "en") =>
  post<AssistantAnswer>("/consumer/query", { query, language });

export const generateChecklist = (
  product: string,
  standard_number?: string | null,
  language: Language = "en",
) => post<ComplianceChecklist>("/compliance/generate", { product, standard_number, language });

export const translate = (text: string, target_language: Language) =>
  post<{ text: string; translated: boolean; reason?: string }>("/translate", {
    text,
    target_language,
  });

// --------------------------------------------------------------------------
// Auth + admin
// --------------------------------------------------------------------------
export const login = (username: string, password: string) =>
  post<{ access_token: string; role: string; username: string }>("/auth/login", {
    username,
    password,
  });

export const adminStats = () => request<Record<string, unknown>>("/admin/stats");
export const adminDocuments = () => request<Record<string, unknown>[]>("/admin/documents");
export const adminFailed = () => request<Record<string, unknown>[]>("/admin/documents/failed");
export const adminQueries = () => request<Record<string, unknown>[]>("/admin/queries");
export const adminQuality = () => request<Record<string, unknown>>("/admin/retrieval-quality");
export const adminReindex = () => post<Record<string, unknown>>("/admin/reindex", {});

export const adminUpload = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return request<Record<string, unknown>>("/admin/documents/upload", {
    method: "POST",
    body: form,
  });
};

export const adminDeleteDocument = (id: string) =>
  request<Record<string, unknown>>(`/admin/documents/${id}`, { method: "DELETE" });

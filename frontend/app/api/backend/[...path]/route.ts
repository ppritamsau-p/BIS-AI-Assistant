/**
 * Server-side proxy to the FastAPI backend.
 *
 * The browser only ever calls /api/backend/*. The real backend origin stays in server
 * environment, no API key is ever shipped to the client, and there is no CORS surface to
 * configure. Streaming responses (the SSE chat endpoint) are piped through untouched so
 * the client still receives events incrementally.
 */
import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE = process.env.BIS_API_BASE ?? "http://127.0.0.1:8000";

// Headers that must not be forwarded verbatim in either direction.
const STRIP_REQUEST = new Set(["host", "connection", "content-length"]);
const STRIP_RESPONSE = new Set(["content-encoding", "content-length", "transfer-encoding"]);

async function forward(req: NextRequest, path: string[]) {
  const target = new URL(`${API_BASE}/${path.join("/")}`);
  req.nextUrl.searchParams.forEach((value, key) => target.searchParams.append(key, value));

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!STRIP_REQUEST.has(key.toLowerCase())) headers.set(key, value);
  });

  const hasBody = !["GET", "HEAD"].includes(req.method);

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? req.body : undefined,
      // Required by undici when streaming a request body through.
      ...(hasBody ? { duplex: "half" } : {}),
      cache: "no-store",
      redirect: "manual",
    } as RequestInit);
  } catch (error) {
    return Response.json(
      {
        detail:
          "The BIS assistant backend is not reachable. Start it with " +
          "`uvicorn backend.main:app --port 8000` from the project root.",
        error: String(error),
      },
      { status: 503 },
    );
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!STRIP_RESPONSE.has(key.toLowerCase())) responseHeaders.set(key, value);
  });

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

type Ctx = { params: { path: string[] } };

export const GET = (req: NextRequest, { params }: Ctx) => forward(req, params.path);
export const POST = (req: NextRequest, { params }: Ctx) => forward(req, params.path);
export const PUT = (req: NextRequest, { params }: Ctx) => forward(req, params.path);
export const PATCH = (req: NextRequest, { params }: Ctx) => forward(req, params.path);
export const DELETE = (req: NextRequest, { params }: Ctx) => forward(req, params.path);

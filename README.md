# BIS AI Intelligent Assistant

AI decision support for **Indian Standards and BIS services** — built for the Smart India
Hackathon problem statement *"AI-Powered Intelligent Assistant for Indian Standards and BIS
Services for Industries and Consumers."*

Describe a product in plain language and get the Indian Standards that may apply, ranked,
with an explanation of *why* each matched and a clause-and-page citation for every claim.

---

## The core idea

This is **not a chatbot with a BIS-flavoured system prompt**. It is a retrieval system that
has to show its work.

```
User query
  → Intent detection + product understanding
  → Query expansion
  → Hybrid retrieval  (BM25 keyword  +  dense vector)
  → Reciprocal Rank Fusion → domain reranking → admissibility gate
  → Grounded composition   (only from retrieved evidence)
  → Guardrail verification (unsupported citations stripped)
  → Structured answer + confidence + sources
```

The model is never asked to recall BIS facts. It is handed retrieved passages and asked to
explain them. When the corpus cannot support an answer, the system says so:

> I could not verify this information from the available BIS knowledge sources.

That refusal is not cosmetic — it is enforced by an absolute relevance gate in the
retriever (see *Why refusal is hard* below).

---

## Quick start

Runs with **no API key, no database, no Docker**. Two terminals:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Open <http://localhost:3000>. The API docs are at <http://localhost:8000/docs>.

> If those ports are busy, run the backend on another port and point the frontend at it:
> `BIS_API_BASE=http://127.0.0.1:8010 npm run dev`

### With Docker

```bash
cp .env.example .env
docker compose up --build
```

This adds PostgreSQL + pgvector and the OCR toolchain for scanned PDFs.

### Enabling the language model

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Without it the **extractive composer** runs instead: answers are assembled directly from
retrieved passages and catalogue records. Less fluent, but incapable of inventing BIS
content — which makes it a genuine no-hallucination baseline rather than a degraded mode.
The UI labels which generator produced every answer.

---

## What is built

| Area | Route | Notes |
|---|---|---|
| Landing page | `/` | Hero search, live index stats, pipeline explainer |
| AI assistant | `/assistant` | Streaming chat, saved answers, local history |
| Product → standards | `/standards/recommend` | The main USP: profile extraction + explainable ranking |
| Standards catalogue | `/standards` | Search + status/industry/category/year facets |
| Compare standards | `/standards/compare` | Side-by-side, up to 4 |
| Certification | `/certification` | 9-step interactive workflow + scheme cards |
| Compliance checklist | `/checklist` | 10 items, progress tracked per product |
| Testing laboratories | `/labs` | Filter by product, standard, test type, location |
| Hallmarking | `/hallmarking` | Gold, silver, HUID, centres, consumer verification |
| Consumer help | `/consumer` | Plain-language marks, verification, complaints |
| Admin console | `/admin` | Upload/index/remove documents, query logs, retrieval quality |
| About | `/about` | Architecture and stated limitations |

**API:** `POST /api/chat`, `/api/chat/stream` (SSE), `/api/standards/{search,recommend,compare}`,
`/api/certification/analyze`, `/api/labs/search`, `/api/hallmarking/query`,
`/api/compliance/generate`, `/api/translate`, `/api/auth/login`, `/api/admin/*`.

**Languages:** English, हिंदी, বাংলা. UI strings are translated in `frontend/lib/i18n.tsx`;
answers are generated in the requested language by the backend. Adding a language means
adding one dictionary entry.

**Voice:** speech-to-text and text-to-speech via the Web Speech API, so audio stays on the
user's device. The button is hidden in browsers that do not support it, rather than shown
and broken.

---

## Design decisions worth explaining

### Why hybrid retrieval is mandatory, not a nice-to-have

Two query shapes must both work:

- `IS 15111` — an exact designation. Dense vectors blur identifiers, so **BM25** carries this.
- `steel lunch box for school children` — never uses the vocabulary of a scope clause. **Dense
  vectors** carry this.

The tokeniser keeps designations intact as single tokens (`IS 302-1` → `is302p1`), so a
designation cannot be diluted into the very common tokens `is` and `302`.

### Why refusal is hard, and how it actually works

Reciprocal Rank Fusion is **rank-based**: the top result of a hopeless query scores exactly as
high as the top result of a perfect one. Asking *"how do I bake a cake"* returned BIS clauses at
score ≈ 1.0 until an **absolute admissibility gate** was added — a chunk is evidence only if it
has an exact designation match, real lexical overlap, or genuine semantic similarity. That gate
is what makes "I could not verify this" possible, and it is covered by tests.

### Three guardrail layers

1. **Structural** — the model only ever sees the retrieved evidence block. No corpus access, no
   web access, no tools.
2. **Instructional** — the system prompt forbids inventing standard numbers, clauses,
   requirements or laboratory details, and mandates explicit refusal over a guess.
3. **Verification** — after generation, every cited designation is checked against the evidence.
   Unsupported ones are rewritten as `[unverified: IS 99999]` and reported in guardrail notes
   rather than silently deleted. Statements of legal obligation are softened unless the evidence
   establishes mandatory status.

*An instruction that is never checked is only an assumption.*

### The domain trap the system is built to avoid

**A standard existing for a product does not make certification mandatory.** That depends on
whether the product is notified under a Quality Control Order or the Compulsory Registration
Scheme. Conflating the two is the most consequential error this assistant could make, so it is
handled in the system prompt, in a dedicated guardrail, and in the certification UI copy.

### Confidence is a retrieval signal, not a correctness claim

The badge combines evidence strength, corroboration, agreement across standards, and citation
anchors. It is labelled everywhere as the AI system's evidence-confidence indicator and
explicitly **not** an official BIS rating.

---

## Demo scenarios

| # | Ask | Demonstrates |
|---|---|---|
| 1 | *I manufacture stainless steel lunch boxes for school children. Which standards may apply?* | Product profile → IS 14756 (99%) + IS 5522, explainable factors |
| 2 | *How can I obtain BIS certification for my product?* | Procedure answer, no spurious product standard |
| 3 | *What documents are required for certification?* | Document list grounded in the scheme record |
| 4 | *Where can I test my electrical product?* | Standard → lab matching |
| 5 | *What is hallmarking?* | Hallmarking corpus, HUID explanation |
| 6 | *Explain IS 302 in simple language* (switch to বাংলা) | Partial designation → IS 302-1, multilingual |
| 7 | Compare IS 14756 and IS 5522 | Evidence-backed comparison, gaps marked unavailable |
| 8 | *How do I bake a chocolate cake?* | **Refusal** — the most important demo |

---

## Data and provenance

The loaded knowledge base is **demo data**, labelled at every level: in the JSON files, on every
API response, on every card in the UI, and in a dismissible banner.

Laboratory records are deliberately **placeholder entries with no contact details**, so no demo
row can be mistaken for a real recognised laboratory. The lab finder never generates results —
it only filters the loaded dataset, and says so on the page.

**Replace `data/` with authorized BIS sources before any real use.** Nothing here should inform
a compliance decision.

---

## Project structure

```
bis-ai-assistant/
├── backend/
│   ├── main.py              FastAPI app, CORS, rate limiting
│   ├── config.py            env-driven settings with working defaults
│   ├── api/                 chat, standards, services, admin routers
│   ├── ai/                  prompts, intent, composer, guardrails, confidence, llm
│   ├── rag/                 ingestion (PDF/OCR), chunking, embeddings
│   ├── retrieval/           tokeniser, BM25, vector index, hybrid fusion
│   ├── database/            in-memory store + PostgreSQL/pgvector driver
│   ├── services/            auth, compliance, comparison
│   └── tests/               44 tests, focused on silent-failure modes
├── frontend/                Next.js 14 App Router, Tailwind, lucide-react
│   ├── app/                 14 routes + server-side API proxy
│   ├── components/          answer rendering, chrome, search, UI primitives
│   └── lib/                 typed API client, i18n, types
├── data/                    demo corpus (standards, certification, labs, hallmarking)
├── scripts/                 ingest_documents · create_embeddings · index_documents
├── docker-compose.yml
└── .env.example
```

---

## Operations

```bash
# Rebuild the index, verify it is usable, run retrieval smoke probes
python scripts/index_documents.py --check --probe

# Ingest documents (PDF with OCR fallback, TXT, MD)
python scripts/ingest_documents.py path/to/docs --recursive

# Build embeddings and persist the vectoriser weights
python scripts/create_embeddings.py

# Tests
python -m pytest backend/tests -q
```

`--check` is meant for CI: an empty or anchor-less index is a silent failure — the assistant
keeps answering, just from thin evidence.

---

## Security

JWT auth (HS256) with admin/user roles, PBKDF2-SHA256 password hashing, per-IP rate limiting,
upload type and size validation, and a server-side proxy so the browser never sees the backend
origin or any API key. Model calls are server-side only.

**Before deploying:** change `JWT_SECRET`, set `ADMIN_PASSWORD` / `USER_PASSWORD`, and move users
out of `backend/services/auth.py` into the database. The demo credentials (`admin`/`admin123`)
are development defaults.

---

## Known limitations

- The knowledge base is demo data, not an official BIS extract.
- The default embedder is a deterministic offline vectoriser, chosen so the prototype runs with
  no external service. It is weaker than a trained sentence encoder — set
  `EMBEDDING_PROVIDER=sbert` and raise `MIN_SEMANTIC_SCORE` to ~0.5 for better recall.
- Rate limiting is in-process; behind multiple workers it needs Redis.
- Conversation history lives in browser storage, not the database.
- The stack is FastAPI-only. The problem brief also listed a Java Spring Boot tier; the modular
  API layer would sit behind such a gateway unchanged, but adding one now would cost build
  complexity without changing what the prototype demonstrates.

---

Not affiliated with or endorsed by the Bureau of Indian Standards. Always verify against
official BIS sources.

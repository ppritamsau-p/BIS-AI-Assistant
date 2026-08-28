"use client";

import {
  Award,
  Bookmark,
  BookmarkCheck,
  Building2,
  Gem,
  MessageSquare,
  Plus,
  ShieldCheck,
  Trash2,
  User,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { AnswerView } from "@/components/answer";
import { PipelineTrace, SearchBox, SpeakButton } from "@/components/search-box";
import { ErrorBox, Spinner } from "@/components/ui";
import { chatStream, type StageEvent } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AssistantAnswer } from "@/lib/types";

interface Turn {
  id: string;
  question: string;
  answer: AssistantAnswer | null;
  error: string | null;
}

interface Conversation {
  id: string;
  title: string;
  turns: Turn[];
  updatedAt: number;
}

const STORAGE_KEY = "bis_conversations";
const SAVED_KEY = "bis_saved_answers";

const SIDEBAR_LINKS = [
  { href: "/standards", icon: ShieldCheck, key: "nav.standards" as const },
  { href: "/certification", icon: Award, key: "nav.certification" as const },
  { href: "/labs", icon: Building2, key: "nav.labs" as const },
  { href: "/hallmarking", icon: Gem, key: "nav.hallmarking" as const },
];

function AssistantInner() {
  const { t, language } = useI18n();
  const params = useSearchParams();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stages, setStages] = useState<StageEvent[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const seededRef = useRef(false);

  // -- persistence -------------------------------------------------------
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: Conversation[] = JSON.parse(raw);
        setConversations(parsed);
        if (parsed.length) setActiveId(parsed[0].id);
      }
      const saved = window.localStorage.getItem(SAVED_KEY);
      if (saved) setSavedIds(JSON.parse(saved));
    } catch {
      /* storage unavailable - the session simply starts empty */
    }
  }, []);

  const persist = useCallback((next: Conversation[]) => {
    setConversations(next);
    try {
      // Keep the most recent conversations only; localStorage is small.
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next.slice(0, 20)));
    } catch {
      /* quota or private mode - in-memory state still works */
    }
  }, []);

  const active = conversations.find((c) => c.id === activeId) ?? null;

  // -- asking ------------------------------------------------------------
  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || loading) return;

      const turnId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const conversationId = activeId ?? turnId;
      const newTurn: Turn = { id: turnId, question: text, answer: null, error: null };

      setConversations((prev) => {
        const existing = prev.find((c) => c.id === conversationId);
        const updated: Conversation = existing
          ? { ...existing, turns: [...existing.turns, newTurn], updatedAt: Date.now() }
          : {
              id: conversationId,
              title: text.slice(0, 60),
              turns: [newTurn],
              updatedAt: Date.now(),
            };
        return [updated, ...prev.filter((c) => c.id !== conversationId)];
      });
      setActiveId(conversationId);
      setInput("");
      setStages([]);
      setLoading(true);

      try {
        const answer = await chatStream(text, language, (stage) =>
          setStages((prev) => [...prev, stage]),
        );
        setConversations((prev) => {
          const next = prev.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  turns: c.turns.map((turn) =>
                    turn.id === turnId ? { ...turn, answer } : turn,
                  ),
                }
              : c,
          );
          try {
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next.slice(0, 20)));
          } catch {
            /* non-fatal */
          }
          return next;
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setConversations((prev) =>
          prev.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  turns: c.turns.map((turn) =>
                    turn.id === turnId ? { ...turn, error: message } : turn,
                  ),
                }
              : c,
          ),
        );
      } finally {
        setLoading(false);
        setStages([]);
      }
    },
    [activeId, language, loading],
  );

  // Seed from ?q= exactly once, so a shared link opens straight into an answer.
  useEffect(() => {
    const q = params.get("q");
    if (q && !seededRef.current) {
      seededRef.current = true;
      void ask(q);
    }
  }, [params, ask]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [active?.turns.length, loading, stages.length]);

  const toggleSaved = (turnId: string) => {
    const next = savedIds.includes(turnId)
      ? savedIds.filter((id) => id !== turnId)
      : [...savedIds, turnId];
    setSavedIds(next);
    try {
      window.localStorage.setItem(SAVED_KEY, JSON.stringify(next));
    } catch {
      /* non-fatal */
    }
  };

  const savedTurns = conversations
    .flatMap((c) => c.turns)
    .filter((turn) => savedIds.includes(turn.id));

  return (
    <div className="container-page grid gap-6 py-8 lg:grid-cols-[16rem_1fr]">
      {/* ---------------------------------------------------------------- */}
      {/* Sidebar                                                          */}
      {/* ---------------------------------------------------------------- */}
      <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
        <button
          onClick={() => {
            setActiveId(null);
            setInput("");
            seededRef.current = true;
          }}
          className="btn-primary w-full"
        >
          <Plus className="h-4 w-4" aria-hidden />
          {t("assistant.newChat")}
        </button>

        <div>
          <p className="section-title mb-2">{t("assistant.recent")}</p>
          {conversations.length === 0 ? (
            <p className="px-1 text-xs text-ink-400">No conversations yet.</p>
          ) : (
            <ul className="space-y-1">
              {conversations.slice(0, 8).map((c) => (
                <li key={c.id} className="group flex items-center gap-1">
                  <button
                    onClick={() => setActiveId(c.id)}
                    className={`flex-1 truncate rounded-lg px-2.5 py-2 text-left text-xs transition ${
                      c.id === activeId
                        ? "bg-ink-900 text-white"
                        : "text-ink-600 hover:bg-ink-50 hover:text-ink-900"
                    }`}
                    title={c.title}
                  >
                    {c.title}
                  </button>
                  <button
                    onClick={() => {
                      const next = conversations.filter((x) => x.id !== c.id);
                      persist(next);
                      if (activeId === c.id) setActiveId(next[0]?.id ?? null);
                    }}
                    aria-label={`Delete ${c.title}`}
                    className="rounded p-1 text-ink-300 opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {savedTurns.length > 0 && (
          <div>
            <p className="section-title mb-2">{t("assistant.saved")}</p>
            <ul className="space-y-1">
              {savedTurns.slice(0, 6).map((turn) => (
                <li key={turn.id}>
                  <span className="flex items-start gap-1.5 rounded-lg px-2.5 py-2 text-xs text-ink-600">
                    <BookmarkCheck className="mt-0.5 h-3 w-3 shrink-0 text-emerald-600" aria-hidden />
                    <span className="line-clamp-2">{turn.question}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <p className="section-title mb-2">Browse</p>
          <ul className="space-y-1">
            {SIDEBAR_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-ink-600 transition hover:bg-ink-50 hover:text-ink-900"
                >
                  <link.icon className="h-3.5 w-3.5 text-ink-400" aria-hidden />
                  {t(link.key)}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* ---------------------------------------------------------------- */}
      {/* Conversation                                                     */}
      {/* ---------------------------------------------------------------- */}
      <div className="min-w-0">
        <div className="mb-6 space-y-8">
          {!active || active.turns.length === 0 ? (
            <div className="card px-6 py-14 text-center">
              <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-ink-900 text-white">
                <MessageSquare className="h-6 w-6" aria-hidden />
              </span>
              <h2 className="mt-4 text-lg font-bold text-ink-950">{t("assistant.emptyTitle")}</h2>
              <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                {t("assistant.emptyBody")}
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {[
                  "I manufacture stainless steel lunch boxes. Which standards may apply?",
                  "What documents are required for certification?",
                  "How does HUID work?",
                ].map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="rounded-full border border-ink-200 bg-white px-3.5 py-1.5 text-xs text-ink-700 transition hover:border-ink-300 hover:bg-ink-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            active.turns.map((turn) => (
              <article key={turn.id} className="space-y-4">
                {/* Question */}
                <div className="flex justify-end">
                  <div className="flex max-w-2xl items-start gap-3 rounded-2xl rounded-tr-sm bg-ink-900 px-4 py-3 text-sm text-white">
                    <p className="flex-1 leading-relaxed">{turn.question}</p>
                    <User className="mt-0.5 h-4 w-4 shrink-0 opacity-60" aria-hidden />
                  </div>
                </div>

                {/* Answer */}
                {turn.error ? (
                  <ErrorBox message={turn.error} onRetry={() => ask(turn.question)} />
                ) : turn.answer ? (
                  <>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <SpeakButton text={turn.answer.answer} language={language} />
                      <button
                        onClick={() => toggleSaved(turn.id)}
                        className="btn-ghost !py-1.5 !text-xs"
                        aria-pressed={savedIds.includes(turn.id)}
                      >
                        {savedIds.includes(turn.id) ? (
                          <>
                            <BookmarkCheck className="h-3.5 w-3.5 text-emerald-600" aria-hidden />
                            {t("assistant.saved.done")}
                          </>
                        ) : (
                          <>
                            <Bookmark className="h-3.5 w-3.5" aria-hidden />
                            {t("assistant.save")}
                          </>
                        )}
                      </button>
                    </div>
                    <AnswerView answer={turn.answer} />
                  </>
                ) : (
                  <div className="space-y-3">
                    <Spinner label={t("common.loading")} />
                    <PipelineTrace stages={stages} />
                  </div>
                )}
              </article>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="sticky bottom-4">
          <SearchBox
            value={input}
            onChange={setInput}
            onSubmit={() => ask(input)}
            loading={loading}
            placeholder={t("assistant.placeholder")}
            submitLabel={t("assistant.send")}
          />
        </div>
      </div>
    </div>
  );
}

export default function AssistantPage() {
  return (
    <Suspense fallback={<div className="container-page py-12" />}>
      <AssistantInner />
    </Suspense>
  );
}

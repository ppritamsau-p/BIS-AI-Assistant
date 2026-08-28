"use client";

import { useState } from "react";
import { AnswerView } from "@/components/answer";
import { PipelineTrace, SearchBox } from "@/components/search-box";
import { ErrorBox, SectionCard, Spinner } from "@/components/ui";
import { type StageEvent } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AssistantAnswer, Language } from "@/lib/types";

/**
 * Reusable "ask a scoped question" panel.
 *
 * The Hallmarking and Consumer sections are the same interaction over a different
 * backend intent, so they share this component rather than duplicating the streaming,
 * error and suggestion handling three times over.
 */
export function AskPanel({
  placeholder,
  suggestions,
  onAsk,
}: {
  placeholder: string;
  suggestions: string[];
  onAsk: (
    question: string,
    language: Language,
    onStage: (stage: StageEvent) => void,
  ) => Promise<AssistantAnswer>;
}) {
  const { t, language } = useI18n();
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [stages, setStages] = useState<StageEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (text = query) => {
    const value = text.trim();
    if (!value || loading) return;

    setQuery(value);
    setLoading(true);
    setError(null);
    setAnswer(null);
    setStages([]);

    try {
      setAnswer(
        await onAsk(value, language, (stage) => setStages((prev) => [...prev, stage])),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStages([]);
    }
  };

  return (
    <>
      <SectionCard className="mb-6">
        <SearchBox
          value={query}
          onChange={setQuery}
          onSubmit={() => ask()}
          placeholder={placeholder}
          loading={loading}
        />

        <div className="mt-4 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="rounded-full border border-ink-200 bg-white px-3.5 py-1.5 text-xs text-ink-700 transition hover:border-ink-300 hover:bg-ink-50"
            >
              {s}
            </button>
          ))}
        </div>

        {loading && (
          <div className="mt-5 space-y-3">
            <Spinner label={t("common.loading")} />
            <PipelineTrace stages={stages} />
          </div>
        )}
        {error && (
          <div className="mt-5">
            <ErrorBox message={error} onRetry={() => ask()} />
          </div>
        )}
      </SectionCard>

      {answer && (
        <div className="mb-10">
          <AnswerView answer={answer} />
        </div>
      )}
    </>
  );
}

"use client";

import { FileSearch, Lightbulb } from "lucide-react";
import { useState } from "react";
import { AnswerView } from "@/components/answer";
import { PipelineTrace } from "@/components/search-box";
import { ErrorBox, PageHeader, SectionCard, Spinner } from "@/components/ui";
import { chatStream, type StageEvent } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AssistantAnswer } from "@/lib/types";

const EXAMPLES = [
  "I manufacture stainless steel lunch boxes for school children.",
  "We produce PVC insulated copper wires for building wiring up to 1100 V.",
  "I make LED bulbs for household lighting.",
  "We manufacture protective helmets for motorcycle riders.",
  "I run a small unit packaging drinking water in 1 litre bottles.",
];

export default function RecommendPage() {
  const { t, language } = useI18n();
  const [description, setDescription] = useState("");
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [stages, setStages] = useState<StageEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (text = description) => {
    const value = text.trim();
    if (!value || loading) return;

    setDescription(value);
    setLoading(true);
    setError(null);
    setAnswer(null);
    setStages([]);

    try {
      // The recommend flow is the chat pipeline with the product-standard intent forced,
      // so it streams the same real stages.
      setAnswer(
        await chatStream(
          `I manufacture the following product. Which Indian Standards may apply? ${value}`,
          language,
          (stage) => setStages((prev) => [...prev, stage]),
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStages([]);
    }
  };

  return (
    <div className="container-page max-w-5xl py-10">
      <PageHeader title={t("recommend.title")} subtitle={t("recommend.subtitle")} />

      <SectionCard>
        <label htmlFor="product-description" className="label">
          {t("recommend.placeholder").split("…")[0]}
        </label>
        <textarea
          id="product-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          placeholder={t("recommend.placeholder")}
          className="input resize-y"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void submit();
          }}
        />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-ink-500">
            Include the material, what it is used for, and who uses it — those three details
            drive most of the matching.
          </p>
          <button
            onClick={() => submit()}
            disabled={loading || !description.trim()}
            className="btn-primary"
          >
            <FileSearch className="h-4 w-4" aria-hidden />
            {t("recommend.submit")}
          </button>
        </div>
      </SectionCard>

      {!answer && !loading && (
        <div className="mt-5">
          <p className="mb-2.5 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-ink-500">
            <Lightbulb className="h-3.5 w-3.5" aria-hidden />
            {t("hero.tryAsking")}
          </p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                onClick={() => submit(example)}
                className="rounded-full border border-ink-200 bg-white px-3.5 py-1.5 text-xs text-ink-700 transition hover:border-ink-300 hover:bg-ink-50"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="mt-6 space-y-3">
          <Spinner label={t("common.loading")} />
          <PipelineTrace stages={stages} />
        </div>
      )}

      {error && (
        <div className="mt-6">
          <ErrorBox message={error} onRetry={() => submit()} />
        </div>
      )}

      {answer && (
        <div className="mt-8">
          <AnswerView answer={answer} />
        </div>
      )}
    </div>
  );
}

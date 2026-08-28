"use client";

import { ClipboardList, RotateCcw } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { SourceChip } from "@/components/answer";
import { EmptyState, ErrorBox, PageHeader, SectionCard, Spinner } from "@/components/ui";
import { generateChecklist } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { ComplianceChecklist } from "@/lib/types";

const PROGRESS_KEY = "bis_checklist_progress";

function ChecklistInner() {
  const { t, language } = useI18n();
  const params = useSearchParams();

  const [product, setProduct] = useState(params.get("product") ?? "");
  const [standard, setStandard] = useState(params.get("standard") ?? "");
  const [checklist, setChecklist] = useState<ComplianceChecklist | null>(null);
  const [done, setDone] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Progress is per-product and lives in the browser: it is the user's working state,
  // not knowledge-base content, so it never goes to the server.
  const progressKey = useCallback(
    (name: string) => `${PROGRESS_KEY}:${name.toLowerCase().trim()}`,
    [],
  );

  const generate = useCallback(
    async (name = product, std = standard) => {
      const value = name.trim();
      if (!value || loading) return;

      setLoading(true);
      setError(null);
      try {
        const result = await generateChecklist(value, std || null, language);
        setChecklist(result);
        try {
          const saved = window.localStorage.getItem(progressKey(value));
          setDone(saved ? JSON.parse(saved) : {});
        } catch {
          setDone({});
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [product, standard, language, loading, progressKey],
  );

  // Auto-generate when arriving from a deep link.
  useEffect(() => {
    const p = params.get("product");
    if (p) void generate(p, params.get("standard") ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggle = (id: string) => {
    if (!checklist) return;
    const next = { ...done, [id]: !done[id] };
    setDone(next);
    try {
      window.localStorage.setItem(progressKey(checklist.product), JSON.stringify(next));
    } catch {
      /* non-fatal */
    }
  };

  const reset = () => {
    if (!checklist) return;
    setDone({});
    try {
      window.localStorage.removeItem(progressKey(checklist.product));
    } catch {
      /* non-fatal */
    }
  };

  const completed = checklist ? checklist.items.filter((i) => done[i.id]).length : 0;
  const total = checklist?.items.length ?? 0;
  const pct = total ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="container-page max-w-4xl py-10">
      <PageHeader title={t("checklist.title")} subtitle={t("checklist.subtitle")} />

      <SectionCard className="mb-8">
        <div className="grid gap-3 sm:grid-cols-[1fr_12rem_auto]">
          <label className="block">
            <span className="label">{t("checklist.product")}</span>
            <input
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && generate()}
              placeholder="e.g. stainless steel lunch box"
              className="input"
            />
          </label>
          <label className="block">
            <span className="label">{t("labs.standard")}</span>
            <input
              value={standard}
              onChange={(e) => setStandard(e.target.value)}
              placeholder="optional"
              className="input font-mono"
            />
          </label>
          <div className="flex items-end">
            <button
              onClick={() => generate()}
              disabled={loading || !product.trim()}
              className="btn-primary w-full sm:w-auto"
            >
              <ClipboardList className="h-4 w-4" aria-hidden />
              {t("checklist.generate")}
            </button>
          </div>
        </div>

        {loading && (
          <div className="mt-4">
            <Spinner label={t("common.loading")} />
          </div>
        )}
        {error && (
          <div className="mt-4">
            <ErrorBox message={error} onRetry={() => generate()} />
          </div>
        )}
      </SectionCard>

      {!checklist && !loading && (
        <EmptyState
          icon={ClipboardList}
          title="No checklist yet"
          body="Describe your product above. The checklist is filled in from the indexed knowledge base — steps it cannot ground are marked as unavailable rather than guessed."
        />
      )}

      {checklist && (
        <>
          {/* Progress */}
          <div className="card mb-5 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink-950">{checklist.product}</p>
                {checklist.standard_number && (
                  <p className="mt-0.5 font-mono text-xs text-ink-500">
                    {checklist.standard_number}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-4">
                <p className="font-mono text-sm font-bold text-ink-900">
                  {completed} / {total}{" "}
                  <span className="font-sans text-xs font-normal text-ink-500">
                    {t("checklist.completed")}
                  </span>
                </p>
                <button onClick={reset} className="btn-ghost !py-1.5 !text-xs">
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden />
                  {t("checklist.reset")}
                </button>
              </div>
            </div>

            <div
              className="mt-4 h-2 overflow-hidden rounded-full bg-ink-100"
              role="progressbar"
              aria-valuenow={pct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${pct}% ${t("checklist.completed")}`}
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-600 transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* Items */}
          <ol className="space-y-3">
            {checklist.items.map((item, i) => {
              const checked = !!done[item.id];
              return (
                <li key={item.id}>
                  <div
                    className={`card p-4 transition ${checked ? "bg-emerald-50/50" : ""}`}
                  >
                    <label className="flex cursor-pointer items-start gap-3">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(item.id)}
                        className="mt-0.5 h-4.5 w-4.5 shrink-0 rounded border-ink-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="min-w-0 flex-1">
                        <span
                          className={`block text-sm font-semibold ${
                            checked ? "text-ink-500 line-through" : "text-ink-950"
                          }`}
                        >
                          {i + 1}. {item.label}
                        </span>
                        {item.detail && (
                          <span className="mt-1.5 block text-xs leading-relaxed text-ink-600">
                            {item.detail}
                          </span>
                        )}
                      </span>
                    </label>

                    {item.source && (
                      <div className="mt-3 pl-7">
                        <SourceChip source={item.source} />
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>

          {checklist.sources.length > 0 && (
            <SectionCard title={t("answer.sources")} className="mt-6">
              <div className="space-y-2">
                {checklist.sources.slice(0, 5).map((s, i) => (
                  <SourceChip key={i} source={s} />
                ))}
              </div>
            </SectionCard>
          )}

          <p className="mt-5 text-xs italic text-ink-500">{t("recommend.disclaimer")}</p>
        </>
      )}
    </div>
  );
}

export default function ChecklistPage() {
  return (
    <Suspense fallback={<div className="container-page py-12" />}>
      <ChecklistInner />
    </Suspense>
  );
}

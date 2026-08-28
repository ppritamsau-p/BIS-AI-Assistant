"use client";

import { BookOpen, GitCompare, Layers, Search, X } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { searchStandards, standardFacets } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Standard } from "@/lib/types";
import { SearchBox } from "@/components/search-box";
import { DemoBadge, EmptyState, ErrorBox, PageHeader, Select, Spinner } from "@/components/ui";

type Facets = { statuses: string[]; industries: string[]; categories: string[]; years: string[] };

function StandardsInner() {
  const { t, language } = useI18n();
  const router = useRouter();
  const params = useSearchParams();

  const [query, setQuery] = useState(params.get("q") ?? "");
  const [status, setStatus] = useState("");
  const [industry, setIndustry] = useState("");
  const [category, setCategory] = useState("");
  const [year, setYear] = useState("");

  const [facets, setFacets] = useState<Facets | null>(null);
  const [results, setResults] = useState<Standard[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    standardFacets().then(setFacets).catch(() => setFacets(null));
  }, []);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const yearNum = year ? Number(year) : null;
      setResults(
        await searchStandards({
          query,
          status: status || null,
          industry: industry || null,
          category: category || null,
          year_from: yearNum,
          year_to: yearNum,
          limit: 50,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [query, status, industry, category, year]);

  // Re-run whenever a filter changes; the query itself is submitted explicitly.
  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, industry, category, year]);

  const anyFilter = status || industry || category || year;

  const toggleSelected = (number: string) =>
    setSelected((prev) =>
      prev.includes(number)
        ? prev.filter((n) => n !== number)
        : prev.length >= 4
          ? prev
          : [...prev, number],
    );

  return (
    <div className="container-page py-10">
      <PageHeader title={t("standards.title")} subtitle={t("standards.subtitle")}>
        <Link href="/standards/recommend" className="btn-secondary">
          <Search className="h-4 w-4" aria-hidden />
          {t("recommend.title")}
        </Link>
      </PageHeader>

      <SearchBox
        value={query}
        onChange={setQuery}
        onSubmit={run}
        placeholder={t("standards.placeholder")}
        loading={loading}
      />

      {/* Filters */}
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Select
          value={status}
          onChange={setStatus}
          options={facets?.statuses ?? []}
          placeholder={`${t("standards.status")} — ${t("common.all")}`}
        />
        <Select
          value={industry}
          onChange={setIndustry}
          options={facets?.industries ?? []}
          placeholder={`${t("standards.industry")} — ${t("common.all")}`}
        />
        <Select
          value={category}
          onChange={setCategory}
          options={facets?.categories ?? []}
          placeholder={`${t("standards.category")} — ${t("common.all")}`}
        />
        <Select
          value={year}
          onChange={setYear}
          options={facets?.years ?? []}
          placeholder={`${t("standards.year")} — ${t("common.all")}`}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-ink-500">
          {loading ? <Spinner /> : `${results.length} ${t("common.results")}`}
        </p>
        <div className="flex items-center gap-2">
          {anyFilter && (
            <button
              onClick={() => {
                setStatus("");
                setIndustry("");
                setCategory("");
                setYear("");
              }}
              className="btn-ghost !py-1.5 !text-xs"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
              {t("common.clear")}
            </button>
          )}
          <button
            disabled={selected.length < 2}
            onClick={() =>
              router.push(`/standards/compare?ids=${encodeURIComponent(selected.join(","))}`)
            }
            className="btn-secondary !py-1.5 !text-xs"
            title={selected.length < 2 ? t("standards.selectToCompare") : undefined}
          >
            <GitCompare className="h-3.5 w-3.5" aria-hidden />
            {t("standards.compareSelected")}
            {selected.length > 0 && ` (${selected.length})`}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-5">
          <ErrorBox message={error} onRetry={run} />
        </div>
      )}

      {/* Results */}
      <div className="mt-5 grid gap-4">
        {!loading && results.length === 0 && !error && (
          <EmptyState
            icon={Layers}
            title={t("common.noResults")}
            body="Try a different keyword, an IS number, or clear the filters."
          />
        )}

        {results.map((std) => {
          const localisedScope =
            (language === "hi" && std.summary_hi) ||
            (language === "bn" && std.summary_bn) ||
            std.scope;
          const isSelected = selected.includes(std.standard_number);

          return (
            <article
              key={std.id}
              className={`card card-hover p-5 ${isSelected ? "ring-2 ring-ink-500" : ""}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-mono text-base font-bold text-ink-950">
                      {std.standard_number}
                    </h2>
                    <span
                      className={`chip ${
                        std.status.toLowerCase() === "active"
                          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                          : "border-ink-200 bg-ink-50 text-ink-600"
                      }`}
                    >
                      {std.status}
                    </span>
                    {std.demo && <DemoBadge />}
                  </div>
                  <p className="mt-1.5 font-medium text-ink-800">{std.title}</p>
                </div>

                <label className="flex shrink-0 cursor-pointer items-center gap-2 text-xs text-ink-600">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelected(std.standard_number)}
                    className="h-4 w-4 rounded border-ink-300 text-ink-900 focus:ring-ink-500"
                  />
                  {t("standards.compare")}
                </label>
              </div>

              {localisedScope && (
                <p className="mt-3 text-sm leading-relaxed text-ink-600">{localisedScope}</p>
              )}

              <dl className="mt-4 grid gap-3 text-xs sm:grid-cols-4">
                <Item label={t("standards.category")} value={std.category} />
                <Item label={t("standards.industry")} value={std.industry} />
                <Item
                  label={t("standards.edition")}
                  value={[std.edition, std.publication_date].filter(Boolean).join(" · ")}
                />
                <Item
                  label={t("standards.related")}
                  value={std.related_standards.join(", ")}
                />
              </dl>

              {std.keywords.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {std.keywords.slice(0, 8).map((k) => (
                    <span key={k} className="chip border-ink-100 bg-surface-muted text-ink-600">
                      {k}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-4 flex flex-wrap gap-2 border-t border-ink-100 pt-4">
                <Link
                  href={`/assistant?q=${encodeURIComponent(`Explain ${std.standard_number} in simple language.`)}`}
                  className="btn-secondary !py-1.5 !text-xs"
                >
                  <BookOpen className="h-3.5 w-3.5" aria-hidden />
                  Explain simply
                </Link>
                <Link
                  href={`/checklist?product=${encodeURIComponent(std.title)}&standard=${encodeURIComponent(std.standard_number)}`}
                  className="btn-ghost !py-1.5 !text-xs"
                >
                  {t("checklist.generate")}
                </Link>
                {std.source_url && (
                  <a
                    href={std.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-ghost !py-1.5 !text-xs"
                  >
                    Official source
                  </a>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-[0.65rem] font-semibold uppercase tracking-wide text-ink-400">{label}</dt>
      <dd className="mt-0.5 text-ink-700">{value}</dd>
    </div>
  );
}

export default function StandardsPage() {
  return (
    <Suspense fallback={<div className="container-page py-12" />}>
      <StandardsInner />
    </Suspense>
  );
}

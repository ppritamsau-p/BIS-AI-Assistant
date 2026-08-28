"use client";

import { Building2, Info, MapPin, ShieldAlert, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { labFacets, searchLabs } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Laboratory } from "@/lib/types";
import { SearchBox } from "@/components/search-box";
import { DemoBadge, EmptyState, ErrorBox, PageHeader, Select, Spinner } from "@/components/ui";

type Facets = {
  states: string[];
  cities: string[];
  categories: string[];
  test_types: string[];
  standards: string[];
};

export default function LabsPage() {
  const { t } = useI18n();

  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [standard, setStandard] = useState("");
  const [testType, setTestType] = useState("");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");

  const [facets, setFacets] = useState<Facets | null>(null);
  const [labs, setLabs] = useState<Laboratory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    labFacets().then(setFacets).catch(() => setFacets(null));
  }, []);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setLabs(
        await searchLabs({
          query,
          product_category: category || null,
          standard_number: standard || null,
          test_type: testType || null,
          state: state || null,
          city: city || null,
          limit: 50,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [query, category, standard, testType, state, city]);

  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, standard, testType, state, city]);

  const anyFilter = category || standard || testType || state || city;

  return (
    <div className="container-page py-10">
      <PageHeader title={t("labs.title")} subtitle={t("labs.subtitle")} />

      {/* Provenance notice: this page must never look AI-generated. */}
      <p className="mb-6 flex items-start gap-2.5 rounded-xl border border-ink-200 bg-white p-3.5 text-xs leading-relaxed text-ink-700">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" aria-hidden />
        {t("labs.noFabrication")}
      </p>

      <SearchBox
        value={query}
        onChange={setQuery}
        onSubmit={run}
        placeholder="Laboratory name, capability or standard…"
        loading={loading}
      />

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Select
          value={category}
          onChange={setCategory}
          options={facets?.categories ?? []}
          placeholder={`${t("labs.category")} — ${t("common.all")}`}
        />
        <Select
          value={standard}
          onChange={setStandard}
          options={facets?.standards ?? []}
          placeholder={`${t("labs.standard")} — ${t("common.all")}`}
        />
        <Select
          value={testType}
          onChange={setTestType}
          options={facets?.test_types ?? []}
          placeholder={`${t("labs.testType")} — ${t("common.all")}`}
        />
        <Select
          value={state}
          onChange={setState}
          options={facets?.states ?? []}
          placeholder={`${t("labs.state")} — ${t("common.all")}`}
        />
        <Select
          value={city}
          onChange={setCity}
          options={facets?.cities ?? []}
          placeholder={`${t("labs.city")} — ${t("common.all")}`}
        />
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-ink-500">
          {loading ? <Spinner /> : `${labs.length} ${t("common.results")}`}
        </p>
        {anyFilter && (
          <button
            onClick={() => {
              setCategory("");
              setStandard("");
              setTestType("");
              setState("");
              setCity("");
            }}
            className="btn-ghost !py-1.5 !text-xs"
          >
            <X className="h-3.5 w-3.5" aria-hidden />
            {t("common.clear")}
          </button>
        )}
      </div>

      {error && (
        <div className="mt-5">
          <ErrorBox message={error} onRetry={run} />
        </div>
      )}

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {!loading && labs.length === 0 && !error && (
          <div className="lg:col-span-2">
            <EmptyState
              icon={Building2}
              title={t("common.noResults")}
              body="No laboratory in the loaded dataset matches these filters. Nothing is generated to fill the gap."
            />
          </div>
        )}

        {labs.map((lab) => (
          <article key={lab.id} className="card card-hover p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-sm font-semibold text-ink-950">{lab.name}</h2>
                <p className="mt-1 flex items-center gap-1.5 text-xs text-ink-500">
                  <MapPin className="h-3 w-3" aria-hidden />
                  {[lab.city, lab.state].filter(Boolean).join(", ")}
                </p>
              </div>
              {lab.demo && <DemoBadge />}
            </div>

            <p className="mt-3 text-xs font-medium text-ink-700">{lab.lab_type}</p>

            <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              <span>
                <span className="font-semibold">{t("labs.recognition")}:</span>{" "}
                {lab.recognition_status}
              </span>
            </div>

            {lab.testing_capabilities.length > 0 && (
              <>
                <p className="section-title mt-4 mb-2">{t("labs.capabilities")}</p>
                <div className="flex flex-wrap gap-1.5">
                  {lab.testing_capabilities.map((cap) => (
                    <span key={cap} className="chip border-ink-100 bg-surface-muted text-ink-600">
                      {cap}
                    </span>
                  ))}
                </div>
              </>
            )}

            {lab.standards_covered.length > 0 && (
              <>
                <p className="section-title mt-4 mb-2">{t("labs.standard")}</p>
                <div className="flex flex-wrap gap-1.5">
                  {lab.standards_covered.map((s) => (
                    <span
                      key={s}
                      className="chip border-ink-200 bg-white font-mono text-ink-700"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </>
            )}

            <dl className="mt-4 border-t border-ink-100 pt-3 text-xs">
              <dt className="font-semibold uppercase tracking-wide text-ink-400">
                {t("labs.contact")}
              </dt>
              <dd className="mt-0.5 italic text-ink-500">{lab.contact}</dd>
            </dl>

            {lab.source_url && (
              <a
                href={lab.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost mt-3 !py-1.5 !text-xs"
              >
                Official source
              </a>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

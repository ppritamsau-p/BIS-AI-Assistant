"use client";

import { GitCompare, Plus, X } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { SourceList } from "@/components/answer";
import { DemoBadge, EmptyState, ErrorBox, PageHeader, Spinner } from "@/components/ui";
import { compareStandards, searchStandards } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { CompareResponse, Standard } from "@/lib/types";

function CompareInner() {
  const { t } = useI18n();
  const params = useSearchParams();

  const [selected, setSelected] = useState<string[]>(
    (params.get("ids") ?? "").split(",").filter(Boolean),
  );
  const [catalogue, setCatalogue] = useState<Standard[]>([]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [picker, setPicker] = useState("");

  useEffect(() => {
    searchStandards({ limit: 100 }).then(setCatalogue).catch(() => setCatalogue([]));
  }, []);

  const run = useCallback(async (numbers: string[]) => {
    if (numbers.length < 2) {
      setResult(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await compareStandards(numbers));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void run(selected);
  }, [selected, run]);

  const add = (number: string) => {
    if (!number || selected.includes(number) || selected.length >= 4) return;
    setSelected([...selected, number]);
    setPicker("");
  };

  const available = catalogue.filter((s) => !selected.includes(s.standard_number));

  return (
    <div className="container-page py-10">
      <PageHeader title={t("compare.title")} subtitle={t("compare.subtitle")}>
        <Link href="/standards" className="btn-secondary">
          {t("standards.title")}
        </Link>
      </PageHeader>

      {/* Selection */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center gap-2">
          {selected.map((number) => (
            <span
              key={number}
              className="chip border-ink-200 bg-ink-50 font-mono text-ink-800"
            >
              {number}
              <button
                onClick={() => setSelected(selected.filter((n) => n !== number))}
                aria-label={`Remove ${number}`}
                className="rounded p-0.5 hover:bg-ink-200"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}

          {selected.length < 4 && (
            <select
              value={picker}
              onChange={(e) => add(e.target.value)}
              className="input max-w-xs !py-1.5 !text-xs"
              aria-label={t("compare.add")}
            >
              <option value="">{t("compare.add")}</option>
              {available.map((s) => (
                <option key={s.id} value={s.standard_number}>
                  {s.standard_number} — {s.title.slice(0, 55)}
                </option>
              ))}
            </select>
          )}
        </div>

        {selected.length < 2 && (
          <p className="mt-3 flex items-center gap-2 text-xs text-ink-500">
            <Plus className="h-3.5 w-3.5" aria-hidden />
            {t("standards.selectToCompare")}
          </p>
        )}
      </div>

      {loading && (
        <div className="mt-6">
          <Spinner label={t("common.loading")} />
        </div>
      )}

      {error && (
        <div className="mt-6">
          <ErrorBox message={error} onRetry={() => run(selected)} />
        </div>
      )}

      {!loading && selected.length < 2 && (
        <div className="mt-6">
          <EmptyState
            icon={GitCompare}
            title={t("standards.selectToCompare")}
            body="Pick standards from the catalogue above. Values are read from the indexed knowledge base — anything it does not hold is shown as unavailable rather than filled in."
          />
        </div>
      )}

      {result && result.standards.length >= 2 && (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[42rem] border-collapse overflow-hidden rounded-2xl border border-ink-100 bg-white text-sm shadow-card">
              <thead>
                <tr className="bg-ink-950 text-white">
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide">
                    {t("compare.parameter")}
                  </th>
                  {result.standards.map((std) => (
                    <th key={std.id} scope="col" className="px-4 py-3 text-left align-top">
                      <span className="block font-mono text-sm font-bold">
                        {std.standard_number}
                      </span>
                      <span className="mt-1 block text-xs font-normal text-ink-300">
                        {std.title}
                      </span>
                      {std.demo && (
                        <span className="mt-1.5 inline-block">
                          <DemoBadge />
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr
                    key={row.parameter}
                    className={i % 2 ? "bg-surface-muted/60" : "bg-white"}
                  >
                    <th
                      scope="row"
                      className="border-t border-ink-100 px-4 py-3 text-left align-top text-xs font-semibold uppercase tracking-wide text-ink-500"
                    >
                      {row.parameter}
                    </th>
                    {result.standards.map((std) => {
                      const value = row.values[std.standard_number] ?? "—";
                      const unavailable = value.startsWith("Not available") || value === "—";
                      return (
                        <td
                          key={std.id}
                          className={`border-t border-ink-100 px-4 py-3 align-top text-sm leading-relaxed ${
                            unavailable ? "italic text-ink-400" : "text-ink-700"
                          }`}
                        >
                          {value}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6">
            <SourceList sources={result.sources} />
          </div>
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="container-page py-12" />}>
      <CompareInner />
    </Suspense>
  );
}

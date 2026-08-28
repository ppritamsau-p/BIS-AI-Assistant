"use client";

import {
  Activity,
  AlertTriangle,
  Building2,
  Database,
  FileText,
  Gem,
  Layers,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  adminDeleteDocument,
  adminDocuments,
  adminFailed,
  adminQuality,
  adminQueries,
  adminReindex,
  adminStats,
  adminUpload,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { EmptyState, ErrorBox, PageHeader, SectionCard, Spinner } from "@/components/ui";

export default function AdminPage() {
  const { t } = useI18n();

  const [authorised, setAuthorised] = useState<boolean | null>(null);
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [documents, setDocuments] = useState<Record<string, any>[]>([]);
  const [failed, setFailed] = useState<Record<string, any>[]>([]);
  const [queries, setQueries] = useState<Record<string, any>[]>([]);
  const [quality, setQuality] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, d, f, q, ql] = await Promise.all([
        adminStats(),
        adminDocuments(),
        adminFailed(),
        adminQueries(),
        adminQuality(),
      ]);
      setStats(s);
      setDocuments(d);
      setFailed(f);
      setQueries(q);
      setQuality(ql);
      setAuthorised(true);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      // 401/403 are an auth state, not a failure to report as an error box.
      if (/auth|token|admin|role/i.test(message)) setAuthorised(false);
      else setError(message);
    }
  }, []);

  useEffect(() => {
    const token = window.localStorage.getItem("bis_token");
    if (!token) {
      setAuthorised(false);
      return;
    }
    void load();
  }, [load]);

  const upload = async (file: File) => {
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      const result = await adminUpload(file);
      setNotice(String(result.message ?? "Document indexed."));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const remove = async (id: string) => {
    setBusy(true);
    try {
      await adminDeleteDocument(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const reindex = async () => {
    setBusy(true);
    setNotice(null);
    try {
      await adminReindex();
      setNotice("Index rebuilt from the data directory.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (authorised === null) {
    return (
      <div className="container-page py-16">
        <Spinner label={t("common.loading")} />
      </div>
    );
  }

  if (!authorised) {
    return (
      <div className="container-page py-16">
        <EmptyState icon={ShieldCheck} title={t("admin.signInRequired")}>
          <Link href="/login" className="btn-primary">
            {t("login.title")}
          </Link>
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="container-page py-10">
      <PageHeader title={t("admin.title")}>
        <button onClick={reindex} disabled={busy} className="btn-secondary">
          <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} aria-hidden />
          {t("admin.reindex")}
        </button>
      </PageHeader>

      {error && (
        <div className="mb-6">
          <ErrorBox message={error} onRetry={load} />
        </div>
      )}
      {notice && (
        <p className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-sm text-emerald-900">
          {notice}
        </p>
      )}

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard icon={ShieldCheck} label={t("admin.totalStandards")} value={stats?.standards} />
        <StatCard icon={FileText} label={t("admin.indexedDocuments")} value={stats?.documents} />
        <StatCard icon={Layers} label={t("admin.indexedChunks")} value={stats?.indexed_chunks} />
        <StatCard
          icon={Database}
          label={t("admin.certificationDocs")}
          value={stats?.certification_schemes}
        />
        <StatCard icon={Building2} label={t("admin.labRecords")} value={stats?.laboratories} />
        <StatCard icon={Gem} label={t("admin.hallmarkingDocs")} value={stats?.hallmarking_topics} />
      </div>

      {/* System row */}
      <div className="mt-4 grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
        <SystemChip label={t("admin.lastUpdate")} value={formatDate(stats?.last_updated)} />
        <SystemChip label="Storage" value={stats?.storage_driver} />
        <SystemChip label="Embeddings" value={stats?.embedding_provider} />
        <SystemChip
          label="Generator"
          value={stats?.llm_enabled ? String(stats?.llm_model) : "extractive (no model configured)"}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        {/* Upload */}
        <SectionCard title={t("admin.upload")} icon={Upload}>
          <label
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-ink-200 bg-surface-muted/60 px-6 py-10 text-center transition hover:border-ink-300 hover:bg-ink-50"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files?.[0];
              if (file) void upload(file);
            }}
          >
            <Upload className="h-6 w-6 text-ink-400" aria-hidden />
            <span className="mt-3 text-sm font-medium text-ink-800">
              Drop a document here, or click to choose
            </span>
            <span className="mt-1 text-xs text-ink-500">{t("admin.uploadHint")}</span>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.md"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void upload(file);
              }}
            />
          </label>
          {busy && (
            <div className="mt-3">
              <Spinner label="Processing and indexing…" />
            </div>
          )}
        </SectionCard>

        {/* Retrieval quality */}
        <SectionCard title={t("admin.quality")} icon={Activity}>
          {!quality || !quality.queries ? (
            <p className="text-sm text-ink-500">
              No queries recorded yet. Ask the assistant something to populate this.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3">
                <QualityStat
                  label="High"
                  value={quality.by_confidence?.high ?? 0}
                  tone="text-emerald-700"
                />
                <QualityStat
                  label="Medium"
                  value={quality.by_confidence?.medium ?? 0}
                  tone="text-amber-700"
                />
                <QualityStat
                  label="Low"
                  value={quality.by_confidence?.low ?? 0}
                  tone="text-red-700"
                />
              </div>
              <dl className="mt-4 space-y-1.5 border-t border-ink-100 pt-3 text-xs">
                <Row label="Queries" value={quality.queries} />
                <Row label="Unanswered (no evidence)" value={quality.unanswered} />
                <Row label="Average top score" value={quality.average_top_score} />
                <Row label="Low-confidence rate" value={quality.low_confidence_rate} />
              </dl>
              {quality.note && (
                <p className="mt-3 text-xs leading-relaxed text-ink-500">{String(quality.note)}</p>
              )}
            </>
          )}
        </SectionCard>
      </div>

      {/* Documents */}
      <SectionCard title={t("admin.documents")} icon={FileText} className="mt-6">
        {documents.length === 0 ? (
          <p className="text-sm text-ink-500">No documents indexed.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-xs">
              <thead className="text-[0.65rem] uppercase tracking-wide text-ink-400">
                <tr>
                  <th className="pb-2 font-semibold">File</th>
                  <th className="pb-2 font-semibold">Standard</th>
                  <th className="pb-2 font-semibold">Type</th>
                  <th className="pb-2 text-right font-semibold">Pages</th>
                  <th className="pb-2 text-right font-semibold">Chunks</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {documents.map((doc) => (
                  <tr key={String(doc.document_id)}>
                    <td className="py-2.5 pr-3 font-medium text-ink-800">{String(doc.filename)}</td>
                    <td className="py-2.5 pr-3 font-mono text-ink-600">
                      {doc.standard_number ? String(doc.standard_number) : "—"}
                    </td>
                    <td className="py-2.5 pr-3 text-ink-600">{String(doc.document_type)}</td>
                    <td className="py-2.5 pr-3 text-right font-mono text-ink-600">
                      {String(doc.pages)}
                    </td>
                    <td className="py-2.5 pr-3 text-right font-mono text-ink-600">
                      {String(doc.chunks)}
                    </td>
                    <td className="py-2.5 text-right">
                      <button
                        onClick={() => remove(String(doc.document_id))}
                        disabled={busy}
                        className="rounded p-1.5 text-ink-400 transition hover:bg-red-50 hover:text-red-600"
                        aria-label={`${t("admin.remove")} ${doc.filename}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* Failed */}
        <SectionCard title={t("admin.failed")} icon={AlertTriangle}>
          {failed.length === 0 ? (
            <p className="text-sm text-ink-500">No ingestion problems recorded.</p>
          ) : (
            <ul className="space-y-2">
              {failed.slice(0, 12).map((entry, i) => (
                <li
                  key={i}
                  className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900"
                >
                  <span className="font-semibold">{String(entry.filename)}</span>
                  <span className="mt-0.5 block">{String(entry.reason)}</span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        {/* Query log */}
        <SectionCard title={t("admin.queries")} icon={Activity}>
          {queries.length === 0 ? (
            <p className="text-sm text-ink-500">No queries recorded yet.</p>
          ) : (
            <ul className="divide-y divide-ink-100">
              {queries.slice(0, 12).map((entry, i) => (
                <li key={i} className="flex items-start gap-3 py-2.5 text-xs">
                  <span
                    className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${
                      entry.confidence === "high"
                        ? "bg-emerald-500"
                        : entry.confidence === "medium"
                          ? "bg-amber-500"
                          : "bg-red-500"
                    }`}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-ink-800">{String(entry.query)}</span>
                    <span className="mt-0.5 block font-mono text-[0.65rem] text-ink-400">
                      {String(entry.intent)} · {String(entry.evidence_count)} passages ·{" "}
                      {String(entry.confidence)}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: unknown;
}) {
  return (
    <div className="card p-4">
      <Icon className="h-4 w-4 text-ink-400" aria-hidden />
      <p className="mt-3 font-mono text-2xl font-bold text-ink-950">
        {value === undefined || value === null ? "—" : String(value)}
      </p>
      <p className="mt-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-ink-400">
        {label}
      </p>
    </div>
  );
}

function SystemChip({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white px-3.5 py-2.5">
      <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-0.5 truncate font-mono text-ink-700" title={String(value ?? "")}>
        {value ? String(value) : "—"}
      </p>
    </div>
  );
}

function QualityStat({ label, value, tone }: { label: string; value: unknown; tone: string }) {
  return (
    <div className="rounded-xl bg-surface-muted p-3 text-center">
      <p className={`font-mono text-lg font-bold ${tone}`}>{String(value)}</p>
      <p className="text-[0.65rem] uppercase tracking-wide text-ink-400">{label}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-500">{label}</dt>
      <dd className="font-mono text-ink-800">{String(value ?? "—")}</dd>
    </div>
  );
}

function formatDate(value: unknown): string {
  if (!value) return "—";
  try {
    return new Date(String(value)).toLocaleString();
  } catch {
    return String(value);
  }
}

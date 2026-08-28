"use client";

import {
  BadgeCheck,
  Beaker,
  BookOpen,
  Building2,
  ChevronDown,
  ClipboardList,
  FileText,
  FlaskConical,
  Info,
  ListChecks,
  Package,
  Quote,
  ShieldQuestion,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useI18n } from "@/lib/i18n";
import type { AssistantAnswer, SourceRef, StandardMatch } from "@/lib/types";
import {
  ConfidenceBadge,
  DemoBadge,
  EmptyState,
  Markdown,
  SectionCard,
  VerifiedBadge,
} from "./ui";

// --------------------------------------------------------------------------
// Sources
// --------------------------------------------------------------------------
export function SourceChip({ source }: { source: SourceRef }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);

  const locator = [
    source.clause ? `${t("common.clause")} ${source.clause}` : null,
    source.page ? `${t("common.page")} ${source.page}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="rounded-xl border border-ink-100 bg-surface-muted/70 p-3">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-start gap-3 text-left"
      >
        <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" aria-hidden />
        <span className="flex-1">
          <span className="block text-sm font-medium text-ink-900">
            {source.standard_number ?? source.title ?? source.document_type}
          </span>
          <span className="mt-0.5 block text-xs text-ink-600">
            {source.standard_number && source.title ? `${source.title} · ` : ""}
            {source.document_type}
            {locator ? ` · ${locator}` : ""}
          </span>
        </span>
        <ChevronDown
          className={`mt-0.5 h-4 w-4 shrink-0 text-ink-400 transition ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>

      {open && (
        <div className="mt-3 border-t border-ink-100 pt-3">
          {source.excerpt && (
            <p className="whitespace-pre-line text-xs leading-relaxed text-ink-700">
              {source.excerpt}
            </p>
          )}
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            {source.standard_number && (
              <Link
                href={`/standards?q=${encodeURIComponent(source.standard_number)}`}
                className="chip border-ink-200 bg-white text-ink-700 hover:border-ink-300"
              >
                <BookOpen className="h-3 w-3" aria-hidden />
                {t("common.viewSource")}
              </Link>
            )}
            <span className="font-mono text-[0.65rem] text-ink-400">
              score {source.score.toFixed(3)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export function SourceList({ sources }: { sources: SourceRef[] }) {
  const { t } = useI18n();
  if (!sources.length) return null;
  return (
    <SectionCard title={t("answer.sources")} icon={FileText}>
      <div className="space-y-2">
        {sources.map((s, i) => (
          <SourceChip key={`${s.chunk_id ?? i}`} source={s} />
        ))}
      </div>
    </SectionCard>
  );
}

// --------------------------------------------------------------------------
// Standard card
// --------------------------------------------------------------------------
export function StandardMatchCard({ match }: { match: StandardMatch }) {
  const { t, language } = useI18n();
  const [showWhy, setShowWhy] = useState(false);
  const std = match.standard;
  const pct = Math.round(match.relevance * 100);

  const localisedScope =
    (language === "hi" && std.summary_hi) || (language === "bn" && std.summary_bn) || std.scope;

  return (
    <article className="card card-hover overflow-hidden">
      <div className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-mono text-base font-bold text-ink-950">{std.standard_number}</h4>
              <span className="chip border-ink-200 bg-ink-50 text-ink-600">{std.status}</span>
              {std.demo && <DemoBadge />}
            </div>
            <p className="mt-1.5 text-sm font-medium text-ink-800">{std.title}</p>
          </div>

          <div className="shrink-0 text-right">
            <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-ink-500">
              {t("answer.relevance")}
            </p>
            <p className="font-mono text-xl font-bold text-ink-900">{pct}%</p>
          </div>
        </div>

        {/* Relevance bar */}
        <div
          className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-100"
          role="meter"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${t("answer.relevance")} ${pct}%`}
        >
          <div
            className="h-full rounded-full bg-gradient-to-r from-ink-500 to-ink-800 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>

        {localisedScope && (
          <p className="mt-4 line-clamp-3 text-sm leading-relaxed text-ink-600">{localisedScope}</p>
        )}

        <dl className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
          <Meta label={t("standards.category")} value={std.category} />
          <Meta label={t("standards.industry")} value={std.industry} />
          <Meta
            label={t("standards.edition")}
            value={[std.edition, std.publication_date].filter(Boolean).join(" · ")}
          />
        </dl>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button onClick={() => setShowWhy((v) => !v)} className="btn-secondary !py-1.5 !text-xs">
            <ShieldQuestion className="h-3.5 w-3.5" aria-hidden />
            {t("answer.whyRecommended")}
          </button>
          <Link
            href={`/standards?q=${encodeURIComponent(std.standard_number)}`}
            className="btn-ghost !py-1.5 !text-xs"
          >
            <BookOpen className="h-3.5 w-3.5" aria-hidden />
            {t("common.viewSource")}
          </Link>
        </div>
      </div>

      {showWhy && (
        <div className="border-t border-ink-100 bg-surface-muted/60 p-5">
          <p className="section-title mb-3">{t("answer.whyRecommended")}</p>

          {Object.keys(match.match_factors).length > 0 && (
            <ul className="mb-3 grid gap-1.5 sm:grid-cols-2">
              {Object.entries(match.match_factors).map(([factor, hit]) => (
                <li
                  key={factor}
                  className={`flex items-center gap-2 text-xs ${
                    hit ? "text-emerald-800" : "text-ink-400"
                  }`}
                >
                  <span aria-hidden>{hit ? "✓" : "○"}</span>
                  {factor}
                </li>
              ))}
            </ul>
          )}

          <ul className="space-y-1.5 text-xs text-ink-700">
            {match.reasons.map((reason, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-ink-400" aria-hidden>
                  ·
                </span>
                {reason}
              </li>
            ))}
          </ul>

          {match.sources.length > 0 && (
            <div className="mt-4 space-y-2">
              {match.sources.map((s, i) => (
                <SourceChip key={i} source={s} />
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-[0.65rem] font-semibold uppercase tracking-wide text-ink-400">{label}</dt>
      <dd className="mt-0.5 text-ink-700">{value}</dd>
    </div>
  );
}

// --------------------------------------------------------------------------
// Full answer
// --------------------------------------------------------------------------
export function AnswerView({ answer }: { answer: AssistantAnswer }) {
  const { t } = useI18n();
  const [showNotes, setShowNotes] = useState(false);

  if (!answer.evidence_found) {
    return (
      <div className="space-y-4 animate-fade-up">
        <EmptyState icon={Info} title={t("answer.noEvidence")} body={answer.answer}>
          <div className="flex flex-wrap justify-center gap-2">
            <Link href="/standards" className="btn-secondary !py-1.5 !text-xs">
              {t("nav.standards")}
            </Link>
            <Link href="/certification" className="btn-secondary !py-1.5 !text-xs">
              {t("nav.certification")}
            </Link>
            <Link href="/assistant" className="btn-secondary !py-1.5 !text-xs">
              {t("nav.askAi")}
            </Link>
          </div>
        </EmptyState>
      </div>
    );
  }

  const cert = answer.certification;
  const testing = answer.testing;

  return (
    <div className="space-y-5 animate-fade-up">
      {/* Answer */}
      <SectionCard>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <VerifiedBadge verified={answer.sources.length > 0} />
          <ConfidenceBadge level={answer.confidence} score={answer.confidence_score} />
          <span className="chip border-ink-100 bg-white text-ink-500">
            <Sparkles className="h-3 w-3" aria-hidden />
            {t("answer.generatedBy")} {answer.generator}
          </span>
        </div>

        <Markdown text={answer.answer} />

        <p className="mt-5 border-t border-ink-100 pt-3 text-xs leading-relaxed text-ink-500">
          {answer.disclaimer}
        </p>
      </SectionCard>

      {/* Product understanding */}
      {answer.product_understanding?.product && (
        <SectionCard title={t("answer.productUnderstanding")} icon={Package}>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Meta label="Product" value={answer.product_understanding.product} />
            <Meta label="Category" value={answer.product_understanding.category} />
            <Meta label="Material" value={answer.product_understanding.materials.join(", ")} />
            <Meta label="Intended use" value={answer.product_understanding.intended_use} />
            <Meta label="Industry" value={answer.product_understanding.industry} />
            <Meta label="Target user" value={answer.product_understanding.target_user} />
            <Meta
              label="Characteristics"
              value={answer.product_understanding.characteristics.join(", ")}
            />
          </dl>
          {answer.product_understanding.notes && (
            <p className="mt-4 text-xs text-ink-500">{answer.product_understanding.notes}</p>
          )}
        </SectionCard>
      )}

      {/* Standards */}
      {answer.standards.length > 0 && (
        <div>
          <h3 className="section-title mb-3 flex items-center gap-2">
            <BadgeCheck className="h-4 w-4" aria-hidden />
            {t("answer.applicableStandards")}
          </h3>
          <div className="grid gap-4">
            {answer.standards.map((m) => (
              <StandardMatchCard key={m.standard.id} match={m} />
            ))}
          </div>
          <p className="mt-3 text-xs italic text-ink-500">{t("recommend.disclaimer")}</p>
        </div>
      )}

      {/* Why match */}
      {answer.why_match.length > 0 && (
        <SectionCard title={t("answer.whyMatch")} icon={ListChecks}>
          <ul className="space-y-2 text-sm text-ink-700">
            {answer.why_match.map((reason, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="mt-0.5 text-emerald-600" aria-hidden>
                  ✓
                </span>
                {reason}
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Certification */}
        {cert && (
          <SectionCard title={t("answer.certification")} icon={BadgeCheck}>
            <p className="rounded-lg bg-ink-50 px-3 py-2 text-sm font-medium text-ink-900">
              {cert.required}
            </p>
            {cert.scheme && (
              <p className="mt-3 text-sm text-ink-700">
                <span className="font-semibold">Scheme:</span> {cert.scheme}
              </p>
            )}
            {cert.process.length > 0 && (
              <>
                <p className="section-title mt-4 mb-2">Process</p>
                <ol className="ml-4 list-decimal space-y-1 text-sm text-ink-700 marker:text-ink-400">
                  {cert.process.slice(0, 6).map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </>
            )}
            {cert.inspection && (
              <>
                <p className="section-title mt-4 mb-1.5">Inspection</p>
                <p className="text-sm text-ink-700">{cert.inspection}</p>
              </>
            )}
          </SectionCard>
        )}

        {/* Testing */}
        {testing && (
          <SectionCard title={t("answer.testing")} icon={Beaker}>
            {testing.tests.length > 0 ? (
              <ul className="space-y-1.5 text-sm text-ink-700">
                {testing.tests.map((test, i) => (
                  <li key={i} className="flex gap-2">
                    <FlaskConical className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" aria-hidden />
                    {test}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-500">
                No specific tests are recorded for this standard in the knowledge base.
              </p>
            )}

            {testing.laboratories.length > 0 && (
              <>
                <p className="section-title mt-4 mb-2">{t("nav.labs")}</p>
                <ul className="space-y-2">
                  {testing.laboratories.map((lab) => (
                    <li
                      key={lab.id}
                      className="flex items-start gap-2 rounded-lg border border-ink-100 bg-surface-muted/60 p-2.5 text-xs"
                    >
                      <Building2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" aria-hidden />
                      <span>
                        <span className="block font-medium text-ink-800">{lab.name}</span>
                        <span className="text-ink-500">
                          {[lab.city, lab.state].filter(Boolean).join(", ")}
                        </span>
                      </span>
                      {lab.demo && <DemoBadge className="ml-auto shrink-0" />}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </SectionCard>
        )}
      </div>

      {/* Documents */}
      {answer.documents.length > 0 && (
        <SectionCard title={t("answer.documents")} icon={ClipboardList}>
          <ul className="grid gap-2 text-sm text-ink-700 sm:grid-cols-2">
            {answer.documents.map((doc, i) => (
              <li key={i} className="flex gap-2">
                <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" aria-hidden />
                {doc}
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      {/* Next steps */}
      {answer.next_steps.length > 0 && (
        <SectionCard title={t("answer.nextSteps")} icon={ListChecks}>
          <ol className="space-y-2.5">
            {answer.next_steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-ink-700">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink-900 text-[0.65rem] font-bold text-white">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </SectionCard>
      )}

      <SourceList sources={answer.sources} />

      {/* Guardrail transparency */}
      {answer.guardrail_notes.length > 0 && (
        <div className="card p-4">
          <button
            onClick={() => setShowNotes((v) => !v)}
            aria-expanded={showNotes}
            className="flex w-full items-center justify-between gap-2 text-left"
          >
            <span className="flex items-center gap-2 text-xs font-semibold text-ink-600">
              <Info className="h-3.5 w-3.5" aria-hidden />
              {t("answer.guardrails")}
            </span>
            <ChevronDown
              className={`h-4 w-4 text-ink-400 transition ${showNotes ? "rotate-180" : ""}`}
              aria-hidden
            />
          </button>
          {showNotes && (
            <ul className="mt-3 space-y-1.5 border-t border-ink-100 pt-3 text-xs text-ink-600">
              {answer.guardrail_notes.map((note, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-ink-300" aria-hidden>
                    ·
                  </span>
                  {note}
                </li>
              ))}
              <li className="mt-2 italic text-ink-400">{t("confidence.note")}</li>
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

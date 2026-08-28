"use client";

import { AlertTriangle, CheckCircle2, Info, Loader2, ShieldCheck, ShieldAlert } from "lucide-react";
import React from "react";
import { useI18n } from "@/lib/i18n";
import type { Confidence } from "@/lib/types";

// --------------------------------------------------------------------------
// Feedback
// --------------------------------------------------------------------------
export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-600">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </span>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="flex-1">
        <p className="font-medium">{t("common.error")}</p>
        <p className="mt-0.5 text-red-800">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary shrink-0 !py-1.5 !text-xs">
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon: Icon = Info,
  title,
  body,
  children,
}: {
  icon?: React.ElementType;
  title: string;
  body?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-200 bg-white/60 px-6 py-12 text-center">
      <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-ink-50 text-ink-500">
        <Icon className="h-5 w-5" aria-hidden />
      </span>
      <p className="text-base font-semibold text-ink-900">{title}</p>
      {body && <p className="mt-1.5 max-w-md text-sm text-ink-600">{body}</p>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

// --------------------------------------------------------------------------
// Provenance
// --------------------------------------------------------------------------
export function DemoBadge({ className = "" }: { className?: string }) {
  const { t } = useI18n();
  return (
    <span
      title="Illustrative record for the prototype - not an official BIS extract."
      className={`chip border-accent-200 bg-accent-50 text-accent-800 ${className}`}
    >
      {t("common.demoData")}
    </span>
  );
}

const CONFIDENCE_STYLES: Record<Confidence, { dot: string; box: string; icon: React.ElementType }> = {
  high: {
    dot: "bg-emerald-500",
    box: "border-emerald-200 bg-emerald-50 text-emerald-900",
    icon: ShieldCheck,
  },
  medium: {
    dot: "bg-amber-500",
    box: "border-amber-200 bg-amber-50 text-amber-900",
    icon: ShieldAlert,
  },
  low: { dot: "bg-red-500", box: "border-red-200 bg-red-50 text-red-900", icon: ShieldAlert },
};

export function ConfidenceBadge({
  level,
  score,
  showScore = true,
}: {
  level: Confidence;
  score?: number;
  showScore?: boolean;
}) {
  const { t } = useI18n();
  const style = CONFIDENCE_STYLES[level];
  const label = t(`confidence.${level}` as const);

  return (
    <span className={`chip ${style.box}`} title={t("confidence.note")}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden />
      {label}
      {showScore && score !== undefined && (
        <span className="font-mono text-[0.65rem] opacity-70">{score.toFixed(2)}</span>
      )}
    </span>
  );
}

export function VerifiedBadge({ verified }: { verified: boolean }) {
  const { t } = useI18n();
  return (
    <span
      className={`chip ${
        verified
          ? "border-ink-200 bg-ink-50 text-ink-700"
          : "border-amber-200 bg-amber-50 text-amber-800"
      }`}
    >
      <CheckCircle2 className="h-3 w-3" aria-hidden />
      {verified ? t("answer.verified") : t("answer.unverified")}
    </span>
  );
}

// --------------------------------------------------------------------------
// Layout helpers
// --------------------------------------------------------------------------
export function SectionCard({
  title,
  icon: Icon,
  action,
  children,
  className = "",
}: {
  title?: string;
  icon?: React.ElementType;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`card p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-ink-900">
            {Icon && <Icon className="h-4 w-4 text-ink-500" aria-hidden />}
            {title}
          </h3>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink-950 sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-sm text-ink-600">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
    </label>
  );
}

export function Select({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder: string;
}) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className="input">
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

// --------------------------------------------------------------------------
// Minimal Markdown
// --------------------------------------------------------------------------
/**
 * Renders the small Markdown subset the assistant actually emits: bold, italics,
 * blockquotes, bullets and paragraphs.
 *
 * Written as React elements rather than `dangerouslySetInnerHTML` on purpose. Answer text
 * can quote passages from ingested documents, and an admin can upload arbitrary files --
 * so this content is not fully trusted and must never reach the DOM as raw HTML.
 */
export function Markdown({ text, className = "" }: { text: string; className?: string }) {
  const blocks = text.trim().split(/\n{2,}/);

  return (
    <div className={`prose-answer space-y-3 ${className}`}>
      {blocks.map((block, i) => {
        const lines = block.split("\n");

        if (lines.every((l) => l.trim().startsWith(">"))) {
          return (
            <blockquote key={i}>
              {inline(lines.map((l) => l.replace(/^\s*>\s?/, "")).join(" "))}
            </blockquote>
          );
        }

        if (lines.every((l) => /^\s*([-*•]|\d+\.)\s+/.test(l))) {
          const ordered = /^\s*\d+\./.test(lines[0]);
          const items = lines.map((l) => l.replace(/^\s*([-*•]|\d+\.)\s+/, ""));
          const List = ordered ? "ol" : "ul";
          return (
            <List
              key={i}
              className={`ml-5 space-y-1.5 ${ordered ? "list-decimal" : "list-disc"} marker:text-ink-400`}
            >
              {items.map((item, j) => (
                <li key={j}>{inline(item)}</li>
              ))}
            </List>
          );
        }

        return <p key={i}>{inline(block.replace(/\n/g, " "))}</p>;
      })}
    </div>
  );
}

/** Inline emphasis: **bold**, *italic*, `code`. */
function inline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g).filter(Boolean);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="rounded bg-ink-100 px-1 py-0.5 font-mono text-[0.85em] text-ink-800">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

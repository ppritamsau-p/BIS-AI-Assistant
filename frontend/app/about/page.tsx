"use client";

import { AlertTriangle, Database, GitBranch, Layers, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getMeta } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Meta } from "@/lib/types";
import { PageHeader, SectionCard } from "@/components/ui";

const PIPELINE = [
  {
    icon: Search,
    title: "Query understanding",
    body: "A deterministic classifier routes the question and, for product descriptions, extracts a structured profile — material, category, intended use, target user. The profile is added to the retrieval query, because scope clauses use vocabulary that customers never do.",
  },
  {
    icon: Layers,
    title: "Hybrid retrieval",
    body: "BM25 over a designation-aware tokeniser runs alongside dense vector search. Exact identifiers like 'IS 302-1' need the lexical half; free-form product prose needs the dense half. Neither alone is sufficient.",
  },
  {
    icon: GitBranch,
    title: "Fusion and reranking",
    body: "Reciprocal Rank Fusion combines the two rankings, then a reranker applies domain signals: exact designation matches, title overlap, clause anchors. An absolute admissibility gate rejects results that only look relevant because they topped an empty ranking.",
  },
  {
    icon: ShieldCheck,
    title: "Grounded composition and verification",
    body: "The answer is composed only from retrieved evidence. Afterwards, every standard number in the text is checked against the evidence, and unsupported ones are struck out and reported rather than silently removed.",
  },
];

export default function AboutPage() {
  const { t } = useI18n();
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  return (
    <div className="container-page max-w-4xl py-10">
      <PageHeader
        title={t("about.title")}
        subtitle="An AI decision-support prototype for Indian Standards and BIS services, built for the Smart India Hackathon."
      />

      <SectionCard className="mb-6">
        <h2 className="text-base font-semibold text-ink-950">What this is</h2>
        <p className="mt-3 text-sm leading-relaxed text-ink-700">
          This is a retrieval-augmented decision-support system, not a general chatbot. It
          answers questions about Indian Standards, BIS certification schemes, testing and
          hallmarking using an indexed corpus of BIS material — and only that corpus. The
          model is never asked to recall BIS facts from training; it is given retrieved
          passages and asked to explain them.
        </p>
        <p className="mt-3 text-sm leading-relaxed text-ink-700">
          The distinction matters because the cost of a confident wrong answer here is real.
          A fabricated clause number or an invented certification requirement can send a
          manufacturer down an expensive dead end. So the system is built to refuse: when the
          corpus cannot support an answer, it says so.
        </p>
      </SectionCard>

      <h2 className="section-title mb-4">How an answer is produced</h2>
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        {PIPELINE.map((step, i) => (
          <article key={step.title} className="card p-5">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink-50 text-ink-700">
                <step.icon className="h-4.5 w-4.5" aria-hidden />
              </span>
              <span className="font-mono text-xs text-ink-400">0{i + 1}</span>
            </div>
            <h3 className="mt-3.5 text-sm font-semibold text-ink-950">{step.title}</h3>
            <p className="mt-2 text-xs leading-relaxed text-ink-600">{step.body}</p>
          </article>
        ))}
      </div>

      <SectionCard title="Three guardrail layers" icon={ShieldCheck} className="mb-6">
        <ol className="space-y-3 text-sm text-ink-700">
          <li className="flex gap-3">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink-900 text-[0.65rem] font-bold text-white">
              1
            </span>
            <span>
              <span className="font-semibold text-ink-900">Structural.</span> The model only
              ever sees retrieved evidence. It has no access to the raw corpus, no web access,
              and no tool with which to reach outside the evidence block.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink-900 text-[0.65rem] font-bold text-white">
              2
            </span>
            <span>
              <span className="font-semibold text-ink-900">Instructional.</span> The system
              prompt forbids inventing standard numbers, clauses, requirements or laboratory
              details, and mandates an explicit "could not verify" response over a guess.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink-900 text-[0.65rem] font-bold text-white">
              3
            </span>
            <span>
              <span className="font-semibold text-ink-900">Verification.</span> After
              generation, cited designations are matched against the evidence, unsupported
              standard cards are dropped, and statements of legal obligation are softened
              unless the evidence establishes mandatory status. An instruction that is never
              checked is only an assumption.
            </span>
          </li>
        </ol>
      </SectionCard>

      <SectionCard title="Limitations" icon={AlertTriangle} className="mb-6">
        <ul className="space-y-2.5 text-sm text-ink-700">
          <li className="flex gap-2.5">
            <span className="text-amber-600" aria-hidden>
              !
            </span>
            The loaded knowledge base is <strong>demo data</strong> — illustrative records for
            exercising the UI and the pipeline, not an official BIS extract. Nothing here should
            be used for a compliance decision.
          </li>
          <li className="flex gap-2.5">
            <span className="text-amber-600" aria-hidden>
              !
            </span>
            The default embedding provider is a deterministic offline vectoriser, chosen so the
            prototype runs with no external service. It is weaker than a trained sentence
            encoder; set <code className="font-mono text-xs">EMBEDDING_PROVIDER=sbert</code> for
            better semantic recall.
          </li>
          <li className="flex gap-2.5">
            <span className="text-amber-600" aria-hidden>
              !
            </span>
            The confidence indicator measures <em>retrieval support</em>, not correctness. It is
            not a BIS rating.
          </li>
          <li className="flex gap-2.5">
            <span className="text-amber-600" aria-hidden>
              !
            </span>
            Laboratory records are deliberately placeholder entries with no contact details, so
            that no demo row can be mistaken for a real recognised laboratory.
          </li>
        </ul>
      </SectionCard>

      {meta && (
        <SectionCard title="Running configuration" icon={Database}>
          <dl className="grid gap-3 text-xs sm:grid-cols-2">
            <Row label="Version" value={meta.version} />
            <Row label="Storage driver" value={meta.storage_driver} />
            <Row label="Embedding provider" value={meta.embedding_provider} />
            <Row label="Answer generator" value={meta.generator} />
            <Row label="Standards indexed" value={meta.standards} />
            <Row label="Evidence passages" value={meta.indexed_chunks} />
            <Row label="Certification schemes" value={meta.certification_schemes} />
            <Row label="Laboratory records" value={meta.laboratories} />
          </dl>
        </SectionCard>
      )}

      <div className="mt-8 flex flex-wrap gap-2">
        <Link href="/assistant" className="btn-primary">
          {t("nav.askAi")}
        </Link>
        <Link href="/standards" className="btn-secondary">
          {t("nav.standards")}
        </Link>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex justify-between gap-3 rounded-lg bg-surface-muted px-3 py-2">
      <dt className="text-ink-500">{label}</dt>
      <dd className="font-mono text-ink-800">{String(value)}</dd>
    </div>
  );
}

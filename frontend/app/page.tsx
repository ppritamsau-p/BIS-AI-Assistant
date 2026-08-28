"use client";

import {
  Award,
  BookOpen,
  Building2,
  Database,
  FileSearch,
  Gem,
  ListChecks,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getMeta } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Meta } from "@/lib/types";
import { SearchBox } from "@/components/search-box";

const SUGGESTIONS = [
  "Which BIS standard applies to stainless steel water bottles?",
  "How can I get BIS certification?",
  "Where can I test my electrical product?",
  "What is hallmarking?",
  "Explain IS 302 in simple language.",
];

const SERVICES = [
  {
    href: "/standards/recommend",
    icon: FileSearch,
    title: "Find Applicable Standards",
    body: "Describe your product and get ranked standards with an explanation of why each one matched.",
  },
  {
    href: "/certification",
    icon: Award,
    title: "Certification Assistant",
    body: "Walk the path from product identification to licence, step by step.",
  },
  {
    href: "/labs",
    icon: Building2,
    title: "Testing Laboratories",
    body: "Filter recognised laboratories by product, standard, test type and location.",
  },
  {
    href: "/hallmarking",
    icon: Gem,
    title: "Hallmarking",
    body: "Gold, silver, HUID, hallmarking centres and consumer verification.",
  },
  {
    href: "/consumer",
    icon: Users,
    title: "Consumer Help",
    body: "Check a mark, verify a product, and understand how to raise a complaint.",
  },
  {
    href: "/checklist",
    icon: ListChecks,
    title: "Compliance Checklist",
    body: "Generate a trackable checklist grounded in the indexed knowledge base.",
  },
];

const PIPELINE = [
  { label: "Query understanding", detail: "Intent + product profile extraction" },
  { label: "Hybrid retrieval", detail: "BM25 keyword + dense vector search" },
  { label: "Reranking", detail: "Designation, title and clause signals" },
  { label: "Grounded answer", detail: "Composed only from retrieved evidence" },
  { label: "Verification", detail: "Unsupported citations stripped" },
];

export default function HomePage() {
  const { t } = useI18n();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  const ask = (text: string) => {
    if (!text.trim()) return;
    router.push(`/assistant?q=${encodeURIComponent(text.trim())}`);
  };

  return (
    <>
      {/* ---------------------------------------------------------------- */}
      {/* Hero                                                             */}
      {/* ---------------------------------------------------------------- */}
      <section className="relative overflow-hidden bg-ink-950">
        <div className="absolute inset-0 grid-bg opacity-40" aria-hidden />
        <div
          className="absolute -left-40 -top-40 h-96 w-96 rounded-full bg-ink-600/25 blur-3xl"
          aria-hidden
        />
        <div
          className="absolute -bottom-52 right-0 h-[28rem] w-[28rem] rounded-full bg-accent-600/10 blur-3xl"
          aria-hidden
        />

        <div className="container-page relative py-20 lg:py-28">
          <div className="mx-auto max-w-3xl text-center">
            <span className="chip mx-auto border-white/15 bg-white/10 text-ink-100 backdrop-blur">
              <Sparkles className="h-3 w-3" aria-hidden />
              Retrieval-augmented · Source verified
            </span>

            <h1 className="mt-6 text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl lg:text-[2.9rem]">
              {t("hero.title")}
            </h1>

            <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-ink-200">
              {t("hero.subtitle")}
            </p>

            <div className="mt-9 text-left">
              <SearchBox
                value={query}
                onChange={setQuery}
                onSubmit={() => ask(query)}
                size="lg"
                placeholder={t("hero.placeholder")}
              />
            </div>

            <div className="mt-6">
              <p className="mb-3 text-xs font-medium uppercase tracking-wider text-ink-400">
                {t("hero.tryAsking")}
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5 text-xs text-ink-100 backdrop-blur transition hover:border-white/30 hover:bg-white/10"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {meta && (
            <dl className="mx-auto mt-14 grid max-w-3xl grid-cols-2 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-4">
              <Stat label="Standards indexed" value={meta.standards} />
              <Stat label="Evidence passages" value={meta.indexed_chunks} />
              <Stat label="Certification schemes" value={meta.certification_schemes} />
              <Stat label="Laboratory records" value={meta.laboratories} />
            </dl>
          )}
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Services                                                         */}
      {/* ---------------------------------------------------------------- */}
      <section className="container-page py-16">
        <h2 className="text-xl font-bold tracking-tight text-ink-950 sm:text-2xl">
          What would you like to do?
        </h2>
        <p className="mt-2 text-sm text-ink-600">
          Every answer links back to the passage it came from.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SERVICES.map((service) => (
            <Link key={service.href} href={service.href} className="card card-hover group p-5">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink-50 text-ink-700 transition group-hover:bg-ink-900 group-hover:text-white">
                <service.icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="mt-4 text-base font-semibold text-ink-950">{service.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{service.body}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* How it works                                                     */}
      {/* ---------------------------------------------------------------- */}
      <section className="border-y border-ink-100 bg-white py-16">
        <div className="container-page">
          <div className="grid gap-12 lg:grid-cols-2">
            <div>
              <span className="section-title">How it works</span>
              <h2 className="mt-3 text-xl font-bold tracking-tight text-ink-950 sm:text-2xl">
                Not a chatbot. A retrieval system that has to show its work.
              </h2>
              <p className="mt-4 text-sm leading-relaxed text-ink-600">
                The assistant answers technical questions only from an indexed BIS corpus. It
                does not answer from model memory, and it does not fill gaps with plausible
                text. When the corpus cannot support an answer, it says so instead of
                guessing — and every standard number it cites is checked against the
                retrieved passages before the response is shown.
              </p>

              <div className="mt-6 flex flex-wrap gap-2">
                <Link href="/assistant" className="btn-primary">
                  <Sparkles className="h-4 w-4" aria-hidden />
                  {t("nav.askAi")}
                </Link>
                <Link href="/about" className="btn-secondary">
                  <BookOpen className="h-4 w-4" aria-hidden />
                  {t("nav.about")}
                </Link>
              </div>
            </div>

            <ol className="relative space-y-1 border-l border-ink-100 pl-6">
              {PIPELINE.map((step, i) => (
                <li key={step.label} className="relative pb-6 last:pb-0">
                  <span className="absolute -left-[1.9rem] flex h-6 w-6 items-center justify-center rounded-full border border-ink-200 bg-white text-[0.65rem] font-bold text-ink-700">
                    {i + 1}
                  </span>
                  <p className="text-sm font-semibold text-ink-900">{step.label}</p>
                  <p className="mt-0.5 text-xs text-ink-500">{step.detail}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Trust                                                            */}
      {/* ---------------------------------------------------------------- */}
      <section className="container-page py-16">
        <div className="grid gap-4 sm:grid-cols-3">
          <TrustCard
            icon={ShieldCheck}
            title="Refuses rather than invents"
            body="Off-topic or unsupported questions return an explicit 'could not verify' response, not a confident-sounding guess."
          />
          <TrustCard
            icon={Search}
            title="Clause-level citations"
            body="Answers carry the standard number, clause and page of the passage they came from, so every claim can be checked."
          />
          <TrustCard
            icon={Database}
            title="Swappable knowledge base"
            body="Demo records today; point it at authorized BIS sources and the same pipeline serves production data."
          />
        </div>
      </section>
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-ink-950/60 px-4 py-5 text-center backdrop-blur">
      <dt className="text-[0.65rem] font-medium uppercase tracking-wider text-ink-400">{label}</dt>
      <dd className="mt-1 font-mono text-2xl font-bold text-white">{value}</dd>
    </div>
  );
}

function TrustCard({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ElementType;
  title: string;
  body: string;
}) {
  return (
    <div className="card p-5">
      <Icon className="h-5 w-5 text-ink-500" aria-hidden />
      <h3 className="mt-3 text-sm font-semibold text-ink-950">{title}</h3>
      <p className="mt-1.5 text-xs leading-relaxed text-ink-600">{body}</p>
    </div>
  );
}

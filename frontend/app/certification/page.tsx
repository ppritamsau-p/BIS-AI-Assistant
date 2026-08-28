"use client";

import { Award, Check, ChevronRight, ClipboardList, FileText, Info } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AnswerView } from "@/components/answer";
import { PipelineTrace } from "@/components/search-box";
import { ErrorBox, PageHeader, SectionCard, Spinner } from "@/components/ui";
import { chatStream, listSchemes, type StageEvent } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AssistantAnswer, CertificationScheme } from "@/lib/types";

/**
 * The nine-step certification path. Kept as static UI copy because it is the *shape* of
 * the process, not a factual claim about any particular product — the product-specific
 * detail comes from the analysed answer and the schemes loaded from the backend.
 */
const STEPS = [
  {
    title: "Identify your product",
    detail:
      "Pin down the exact product, its variants, ratings and intended use. Certification is granted against a specific product at a specific premises.",
  },
  {
    title: "Find the applicable Indian Standard",
    detail:
      "Every licence is issued against a standard. Use the product-to-standard finder if you are not sure which one covers you.",
    link: { href: "/standards/recommend", label: "Find applicable standards" },
  },
  {
    title: "Check whether certification is mandatory",
    detail:
      "A standard existing for your product does not make certification mandatory. That depends on whether the product is notified under a Quality Control Order or the Compulsory Registration Scheme. Check the official list.",
    emphasis: true,
  },
  {
    title: "Identify the certification scheme",
    detail:
      "Scheme-I (ISI Mark) for most products, CRS for notified electronics and IT products, FMCS for overseas manufacturers, and the Hallmarking scheme for precious metal articles.",
  },
  {
    title: "Testing requirements",
    detail:
      "Samples must be tested against every requirement of the applicable standard, at a laboratory recognised by BIS for that product and standard.",
    link: { href: "/labs", label: "Find a testing laboratory" },
  },
  {
    title: "Required documents",
    detail:
      "Firm and address proof, machinery and test equipment lists with calibration records, process flow chart, third-party test reports, QC personnel details and the prescribed undertakings.",
  },
  {
    title: "Application",
    detail:
      "Submit through the BIS online portal with the prescribed fee. Incomplete applications are the most common cause of delay.",
  },
  {
    title: "Inspection",
    detail:
      "A BIS officer verifies the manufacturing process, in-house testing capability and quality control records, and draws samples for independent testing.",
  },
  {
    title: "Licence / certificate",
    detail:
      "Granted once inspection and independent testing are satisfactory. The licence covers only the product applied for, and is subject to ongoing surveillance.",
  },
];

export default function CertificationPage() {
  const { t, language } = useI18n();
  const [input, setInput] = useState("");
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [stages, setStages] = useState<StageEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [schemes, setSchemes] = useState<CertificationScheme[]>([]);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    listSchemes().then(setSchemes).catch(() => setSchemes([]));
  }, []);

  const analyse = async () => {
    const value = input.trim();
    if (!value || loading) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    setStages([]);
    try {
      setAnswer(
        await chatStream(
          `What are the BIS certification requirements for: ${value}`,
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
    <div className="container-page py-10">
      <PageHeader title={t("certification.title")} subtitle={t("certification.subtitle")} />

      {/* Analyser */}
      <SectionCard className="mb-8">
        <label htmlFor="cert-input" className="label">
          {t("certification.describe")}
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="cert-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && analyse()}
            placeholder="e.g. LED bulbs for household lighting, or IS 16102"
            className="input flex-1"
          />
          <button onClick={analyse} disabled={loading || !input.trim()} className="btn-primary">
            <Award className="h-4 w-4" aria-hidden />
            {t("certification.analyze")}
          </button>
        </div>

        {loading && (
          <div className="mt-4 space-y-3">
            <Spinner label={t("common.loading")} />
            <PipelineTrace stages={stages} />
          </div>
        )}
        {error && (
          <div className="mt-4">
            <ErrorBox message={error} onRetry={analyse} />
          </div>
        )}
      </SectionCard>

      {answer && (
        <div className="mb-10">
          <AnswerView answer={answer} />
          <div className="mt-5 flex flex-wrap gap-2">
            <Link
              href={`/checklist?product=${encodeURIComponent(input)}${
                answer.standards[0]
                  ? `&standard=${encodeURIComponent(answer.standards[0].standard.standard_number)}`
                  : ""
              }`}
              className="btn-primary"
            >
              <ClipboardList className="h-4 w-4" aria-hidden />
              {t("certification.generateChecklist")}
            </Link>
          </div>
        </div>
      )}

      {/* Stepper */}
      <h2 className="section-title mb-4">Certification workflow</h2>
      <div className="grid gap-6 lg:grid-cols-[20rem_1fr]">
        <ol className="space-y-1">
          {STEPS.map((step, i) => {
            const active = i === activeStep;
            const done = i < activeStep;
            return (
              <li key={step.title}>
                <button
                  onClick={() => setActiveStep(i)}
                  aria-current={active ? "step" : undefined}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition ${
                    active ? "bg-ink-900 text-white shadow-card" : "hover:bg-white"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[0.65rem] font-bold ${
                      active
                        ? "bg-white text-ink-900"
                        : done
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-ink-100 text-ink-500"
                    }`}
                  >
                    {done ? <Check className="h-3 w-3" aria-hidden /> : i + 1}
                  </span>
                  <span className={`flex-1 text-sm ${active ? "font-semibold" : "text-ink-700"}`}>
                    {step.title}
                  </span>
                  <ChevronRight
                    className={`h-4 w-4 shrink-0 ${active ? "opacity-80" : "opacity-0"}`}
                    aria-hidden
                  />
                </button>
              </li>
            );
          })}
        </ol>

        <SectionCard>
          <div className="flex items-start gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-ink-900 text-sm font-bold text-white">
              {activeStep + 1}
            </span>
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold text-ink-950">{STEPS[activeStep].title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-700">
                {STEPS[activeStep].detail}
              </p>

              {STEPS[activeStep].emphasis && (
                <p className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-900">
                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                  This is the single most misunderstood point in BIS certification. Confirm
                  mandatory status against the official QCO and CRS lists — they change over
                  time.
                </p>
              )}

              {STEPS[activeStep].link && (
                <Link
                  href={STEPS[activeStep].link!.href}
                  className="btn-secondary mt-4 !py-1.5 !text-xs"
                >
                  {STEPS[activeStep].link!.label}
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              )}

              <div className="mt-6 flex justify-between border-t border-ink-100 pt-4">
                <button
                  onClick={() => setActiveStep((s) => Math.max(0, s - 1))}
                  disabled={activeStep === 0}
                  className="btn-ghost !py-1.5 !text-xs"
                >
                  Previous
                </button>
                <button
                  onClick={() => setActiveStep((s) => Math.min(STEPS.length - 1, s + 1))}
                  disabled={activeStep === STEPS.length - 1}
                  className="btn-secondary !py-1.5 !text-xs"
                >
                  Next step
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden />
                </button>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      {/* Schemes */}
      {schemes.length > 0 && (
        <section className="mt-12">
          <h2 className="section-title mb-4">{t("certification.schemes")}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {schemes.map((scheme) => (
              <article key={scheme.id} className="card p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-ink-950">{scheme.scheme_name}</h3>
                  <span
                    className={`chip ${
                      scheme.mandatory
                        ? "border-amber-200 bg-amber-50 text-amber-800"
                        : "border-ink-200 bg-ink-50 text-ink-600"
                    }`}
                  >
                    {scheme.mandatory ? "Mandatory where notified" : "Voluntary by default"}
                  </span>
                </div>
                <p className="mt-2 text-xs text-ink-600">{scheme.product_category}</p>

                <p className="section-title mt-4 mb-2">{t("certification.documents")}</p>
                <ul className="space-y-1 text-xs text-ink-700">
                  {scheme.documents.slice(0, 5).map((doc, i) => (
                    <li key={i} className="flex gap-2">
                      <FileText className="mt-0.5 h-3 w-3 shrink-0 text-ink-400" aria-hidden />
                      {doc}
                    </li>
                  ))}
                </ul>

                {scheme.inspection && (
                  <>
                    <p className="section-title mt-4 mb-1.5">Inspection</p>
                    <p className="text-xs leading-relaxed text-ink-600">{scheme.inspection}</p>
                  </>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

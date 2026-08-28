"use client";

import { BadgeCheck, Building2, Gem, ScanLine, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { AskPanel } from "@/components/ask-panel";
import { DemoBadge, PageHeader, SectionCard } from "@/components/ui";
import { chatStream, hallmarkingTopics } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { HallmarkingTopic } from "@/lib/types";

const SUGGESTIONS = [
  "What is hallmarking?",
  "How does HUID work?",
  "How can I verify a hallmarked product?",
  "What are the hallmarking requirements for a jeweller?",
  "What is the process for jewellers to register?",
];

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  Gold: Sparkles,
  Silver: Gem,
  HUID: ScanLine,
  "Hallmarking Centre": Building2,
  "Consumer Verification": ShieldCheck,
  "Jeweller Process": BadgeCheck,
};

export default function HallmarkingPage() {
  const { t } = useI18n();
  const [topics, setTopics] = useState<HallmarkingTopic[]>([]);

  useEffect(() => {
    hallmarkingTopics().then(setTopics).catch(() => setTopics([]));
  }, []);

  return (
    <div className="container-page py-10">
      <PageHeader title={t("hallmarking.title")} subtitle={t("hallmarking.subtitle")} />

      <AskPanel
        placeholder={t("hallmarking.ask")}
        suggestions={SUGGESTIONS}
        onAsk={(question, language, onStage) =>
          chatStream(`About BIS hallmarking: ${question}`, language, onStage)
        }
      />

      <h2 className="section-title mb-4">Topics</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {topics.map((topic) => {
          const Icon = CATEGORY_ICONS[topic.category] ?? Gem;
          return (
            <article key={topic.id} className="card card-hover p-5">
              <div className="flex items-start justify-between gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink-50 text-ink-700">
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                {topic.demo && <DemoBadge />}
              </div>

              <h3 className="mt-4 text-sm font-semibold text-ink-950">{topic.topic}</h3>
              <p className="mt-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-ink-400">
                {topic.category}
              </p>
              <p className="mt-2.5 text-xs leading-relaxed text-ink-600">{topic.summary}</p>

              {topic.details.length > 0 && (
                <ul className="mt-3 space-y-1.5 border-t border-ink-100 pt-3 text-xs text-ink-600">
                  {topic.details.map((detail, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-ink-300" aria-hidden>
                        ·
                      </span>
                      {detail}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          );
        })}
      </div>

      <SectionCard className="mt-8">
        <p className="text-xs leading-relaxed text-ink-600">
          <span className="font-semibold text-ink-800">Verifying a HUID:</span> a hallmark
          certifies the purity of the precious metal only — not the weight of the article, the
          making charges, or the value of any stones set into it. Use the official BIS
          verification facility to check a HUID against the hallmarking database, and keep an
          invoice recording the net precious-metal weight, purity, hallmarking charges and the
          HUID.
        </p>
      </SectionCard>
    </div>
  );
}

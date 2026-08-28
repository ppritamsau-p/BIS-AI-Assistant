"use client";

import { AlertCircle, BadgeCheck, HelpCircle, MessageSquareWarning, ShieldCheck } from "lucide-react";
import { AskPanel } from "@/components/ask-panel";
import { PageHeader, SectionCard } from "@/components/ui";
import { consumerQuery } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const SUGGESTIONS = [
  "How do I check if a product is really BIS certified?",
  "What does the ISI mark mean?",
  "How do I complain about a product with a fake BIS mark?",
  "Is every product required to carry the BIS mark?",
  "What should I check before buying a helmet?",
];

const HELP_CARDS = [
  {
    icon: BadgeCheck,
    title: "Verify a certified product",
    body: "The mark should show the Standard Mark, the Indian Standard number and a licence or registration number. A mark without a verifiable number should be treated with suspicion.",
  },
  {
    icon: ShieldCheck,
    title: "What the mark does and does not mean",
    body: "It means the manufacturer holds a valid licence to declare conformity to a specific Indian Standard. It is not a quality ranking against other brands, and not a lifespan guarantee.",
  },
  {
    icon: MessageSquareWarning,
    title: "Raising a complaint",
    body: "Complaints about a marked product that does not conform, or about misuse of the mark, can be lodged with BIS. Keep the invoice and note the licence number shown on the product.",
  },
  {
    icon: AlertCircle,
    title: "Mandatory or voluntary?",
    body: "Certification is mandatory only for products notified under a Quality Control Order or the Compulsory Registration Scheme. For everything else it is voluntary.",
  },
];

const FAQS = [
  {
    q: "Does a BIS mark mean BIS tested this exact unit?",
    a: "No. Conformity is established through testing at a recognised laboratory and, for most schemes, factory inspection and ongoing surveillance. It does not mean BIS tested the individual unit you bought.",
  },
  {
    q: "What if a hallmarked article turns out to be of lower purity than marked?",
    a: "Take it up with the seller and report it to BIS. A hallmarked article may be re-tested at a recognised Assaying and Hallmarking Centre.",
  },
  {
    q: "Where is the list of products under mandatory certification?",
    a: "It is published by BIS and by the notifying ministries. It changes over time, so it must always be checked against the official source rather than a cached copy.",
  },
  {
    q: "Can I buy the text of an Indian Standard?",
    a: "Indian Standards are published by BIS and can be obtained through its official channels.",
  },
];

export default function ConsumerPage() {
  const { t } = useI18n();

  return (
    <div className="container-page py-10">
      <PageHeader title={t("consumer.title")} subtitle={t("consumer.subtitle")} />

      <AskPanel
        placeholder={t("consumer.ask")}
        suggestions={SUGGESTIONS}
        onAsk={(question, language) => consumerQuery(question, language)}
      />

      <h2 className="section-title mb-4">Quick help</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {HELP_CARDS.map((card) => (
          <article key={card.title} className="card p-5">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink-50 text-ink-700">
              <card.icon className="h-5 w-5" aria-hidden />
            </span>
            <h3 className="mt-4 text-sm font-semibold text-ink-950">{card.title}</h3>
            <p className="mt-2 text-xs leading-relaxed text-ink-600">{card.body}</p>
          </article>
        ))}
      </div>

      <SectionCard title="Frequently asked questions" icon={HelpCircle} className="mt-8">
        <dl className="divide-y divide-ink-100">
          {FAQS.map((faq) => (
            <div key={faq.q} className="py-4 first:pt-0 last:pb-0">
              <dt className="text-sm font-semibold text-ink-950">{faq.q}</dt>
              <dd className="mt-1.5 text-xs leading-relaxed text-ink-600">{faq.a}</dd>
            </div>
          ))}
        </dl>
      </SectionCard>
    </div>
  );
}

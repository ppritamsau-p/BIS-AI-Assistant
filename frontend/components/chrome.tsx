"use client";

import {
  AlertTriangle,
  Award,
  BadgeCheck,
  Building2,
  ChevronDown,
  Globe,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getMeta } from "@/lib/api";
import { LANGUAGES, useI18n } from "@/lib/i18n";
import type { Language, Meta } from "@/lib/types";

const NAV: { href: string; key: Parameters<ReturnType<typeof useI18n>["t"]>[0] }[] = [
  { href: "/", key: "nav.home" },
  { href: "/standards", key: "nav.standards" },
  { href: "/certification", key: "nav.certification" },
  { href: "/labs", key: "nav.labs" },
  { href: "/hallmarking", key: "nav.hallmarking" },
  { href: "/consumer", key: "nav.consumer" },
  { href: "/about", key: "nav.about" },
];

// --------------------------------------------------------------------------
export function LanguageSelector({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage, t } = useI18n();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, [open]);

  const current = LANGUAGES.find((l) => l.code === language);

  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Select language"
        className={
          compact
            ? "inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50"
            : "btn-secondary !py-2 !text-xs"
        }
      >
        <Globe className="h-3.5 w-3.5" aria-hidden />
        {current?.native}
        <ChevronDown className="h-3 w-3 opacity-60" aria-hidden />
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute right-0 z-50 mt-1.5 w-40 overflow-hidden rounded-xl border border-ink-100 bg-white p-1 shadow-lift"
        >
          {LANGUAGES.map((lang) => (
            <li key={lang.code}>
              <button
                role="option"
                aria-selected={lang.code === language}
                onClick={() => {
                  setLanguage(lang.code as Language);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition ${
                  lang.code === language
                    ? "bg-ink-900 text-white"
                    : "text-ink-700 hover:bg-ink-50"
                }`}
              >
                <span>{lang.native}</span>
                <span className="text-[0.65rem] uppercase opacity-60">{lang.code}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------
export function Header() {
  const { t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    setRole(window.localStorage.getItem("bis_role"));
  }, [pathname]);

  const signOut = () => {
    window.localStorage.removeItem("bis_token");
    window.localStorage.removeItem("bis_role");
    setRole(null);
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-white/85 backdrop-blur-lg">
      <div className="container-page flex h-16 items-center gap-4">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink-900 text-white">
            <ShieldCheck className="h-5 w-5" aria-hidden />
          </span>
          <span className="leading-tight">
            <span className="block text-[0.95rem] font-bold tracking-tight text-ink-950">
              BIS AI Assistant
            </span>
            <span className="block text-[0.65rem] font-medium uppercase tracking-wider text-ink-400">
              Indian Standards
            </span>
          </span>
        </Link>

        <nav className="ml-4 hidden flex-1 items-center gap-0.5 lg:flex">
          {NAV.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                  active ? "bg-ink-50 text-ink-950" : "text-ink-600 hover:bg-ink-50 hover:text-ink-900"
                }`}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden sm:block">
            <LanguageSelector compact />
          </span>

          {role === "admin" && (
            <Link href="/admin" className="btn-ghost hidden !py-2 !text-xs sm:inline-flex">
              <LayoutDashboard className="h-3.5 w-3.5" aria-hidden />
              {t("nav.admin")}
            </Link>
          )}

          <Link href="/assistant" className="btn-primary !py-2 !text-xs">
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            {t("nav.askAi")}
          </Link>

          {role ? (
            <button onClick={signOut} className="btn-secondary hidden !py-2 !text-xs sm:inline-flex">
              <LogOut className="h-3.5 w-3.5" aria-hidden />
              {t("nav.logout")}
            </button>
          ) : (
            <Link href="/login" className="btn-secondary hidden !py-2 !text-xs sm:inline-flex">
              {t("nav.login")}
            </Link>
          )}

          <button
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle navigation"
            aria-expanded={mobileOpen}
            className="btn-ghost !p-2 lg:hidden"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="border-t border-ink-100 bg-white lg:hidden">
          <div className="container-page grid gap-0.5 py-3">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-ink-50"
              >
                {t(item.key)}
              </Link>
            ))}
            <div className="mt-2 flex items-center gap-2 border-t border-ink-100 pt-3">
              <LanguageSelector />
              {role ? (
                <button onClick={signOut} className="btn-secondary !py-2 !text-xs">
                  {t("nav.logout")}
                </button>
              ) : (
                <Link href="/login" className="btn-secondary !py-2 !text-xs">
                  {t("nav.login")}
                </Link>
              )}
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}

// --------------------------------------------------------------------------
export function DemoBanner() {
  const { t } = useI18n();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
    try {
      setDismissed(window.sessionStorage.getItem("bis_demo_dismissed") === "1");
    } catch {
      /* storage unavailable - just show the banner */
    }
  }, []);

  if (!meta?.demo_mode || dismissed) return null;

  return (
    <div className="border-b border-accent-200 bg-accent-50">
      <div className="container-page flex items-start gap-3 py-2.5 text-xs text-accent-900">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        <p className="flex-1 leading-relaxed">{t("demo.banner")}</p>
        <button
          onClick={() => {
            setDismissed(true);
            try {
              window.sessionStorage.setItem("bis_demo_dismissed", "1");
            } catch {
              /* non-fatal */
            }
          }}
          aria-label={t("common.close")}
          className="shrink-0 rounded p-0.5 hover:bg-accent-100"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
export function Footer() {
  const { t } = useI18n();
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  return (
    <footer className="mt-16 border-t border-ink-100 bg-white">
      <div className="container-page py-10">
        <div className="grid gap-8 md:grid-cols-4">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink-900 text-white">
                <ShieldCheck className="h-4 w-4" aria-hidden />
              </span>
              <span className="font-bold text-ink-950">BIS AI Assistant</span>
            </div>
            <p className="mt-3 max-w-md text-xs leading-relaxed text-ink-500">
              {t("footer.disclaimer")}
            </p>
            {meta && (
              <dl className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 font-mono text-[0.65rem] text-ink-400">
                <span>v{meta.version}</span>
                <span>{meta.standards} standards</span>
                <span>{meta.indexed_chunks} chunks</span>
                <span>{meta.storage_driver}</span>
                <span>{meta.embedding_provider}</span>
                <span>{meta.generator}</span>
              </dl>
            )}
          </div>

          <FooterColumn
            title={t("nav.standards")}
            links={[
              { href: "/standards", label: t("standards.title") },
              { href: "/standards/recommend", label: t("recommend.title") },
              { href: "/standards/compare", label: t("compare.title") },
            ]}
          />
          <FooterColumn
            title="BIS Services"
            links={[
              { href: "/certification", label: t("certification.title") },
              { href: "/labs", label: t("labs.title") },
              { href: "/hallmarking", label: t("hallmarking.title") },
              { href: "/consumer", label: t("consumer.title") },
              { href: "/checklist", label: t("checklist.title") },
            ]}
          />
        </div>

        <p className="mt-8 border-t border-ink-100 pt-5 text-xs text-ink-400">
          Prototype built for the Smart India Hackathon problem statement on AI-powered
          assistance for Indian Standards and BIS services. Not affiliated with or endorsed
          by the Bureau of Indian Standards.
        </p>
      </div>
    </footer>
  );
}

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: { href: string; label: string }[];
}) {
  return (
    <div>
      <p className="section-title mb-3">{title}</p>
      <ul className="space-y-2">
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="text-xs text-ink-600 hover:text-ink-900">
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export const SERVICE_ICONS = {
  standards: BadgeCheck,
  certification: Award,
  labs: Building2,
  assistant: MessageSquare,
};

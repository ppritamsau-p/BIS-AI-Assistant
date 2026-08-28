"use client";

import { ArrowRight, Loader2, Mic, MicOff, Search, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "@/lib/i18n";
import type { Language } from "@/lib/types";

// --------------------------------------------------------------------------
// Speech recognition (Web Speech API)
// --------------------------------------------------------------------------
const SPEECH_LOCALES: Record<Language, string> = {
  en: "en-IN",
  hi: "hi-IN",
  bn: "bn-IN",
};

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: any) => void) | null;
  onerror: ((e: any) => void) | null;
  onend: (() => void) | null;
};

function getRecognition(): SpeechRecognitionLike | null {
  if (typeof window === "undefined") return null;
  const Ctor =
    (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition ?? null;
  return Ctor ? (new Ctor() as SpeechRecognitionLike) : null;
}

/**
 * Voice input. Uses the browser's own speech recognition, which keeps the audio on the
 * user's device and adds no server dependency. Unsupported browsers (notably Firefox)
 * simply do not render the button rather than showing one that fails.
 */
export function useVoiceInput(language: Language, onTranscript: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    setSupported(getRecognition() !== null);
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  const start = useCallback(() => {
    const recognition = getRecognition();
    if (!recognition) return;

    recognition.lang = SPEECH_LOCALES[language];
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results as ArrayLike<any>)
        .map((r: any) => r[0].transcript)
        .join(" ")
        .trim();
      if (transcript) onTranscript(transcript);
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [language, onTranscript]);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  return { listening, supported, start, stop };
}

/** Text-to-speech for an answer, matching the selected language. */
export function SpeakButton({ text, language }: { text: string; language: Language }) {
  const [speaking, setSpeaking] = useState(false);
  const [supported, setSupported] = useState(false);

  useEffect(() => {
    setSupported(typeof window !== "undefined" && "speechSynthesis" in window);
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  if (!supported) return null;

  const toggle = () => {
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    // Strip Markdown emphasis so the synthesiser does not read asterisks aloud.
    const plain = text.replace(/[*_>`#]/g, "").slice(0, 4000);
    const utterance = new SpeechSynthesisUtterance(plain);
    utterance.lang = SPEECH_LOCALES[language];
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  };

  return (
    <button
      onClick={toggle}
      className="btn-ghost !py-1.5 !text-xs"
      aria-label={speaking ? "Stop reading" : "Read answer aloud"}
    >
      {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
      {speaking ? "Stop" : "Listen"}
    </button>
  );
}

// --------------------------------------------------------------------------
// Search box
// --------------------------------------------------------------------------
export function SearchBox({
  value,
  onChange,
  onSubmit,
  placeholder,
  loading = false,
  size = "md",
  submitLabel,
  autoFocus = false,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  loading?: boolean;
  size?: "md" | "lg";
  submitLabel?: string;
  autoFocus?: boolean;
}) {
  const { t, language } = useI18n();
  const { listening, supported, start, stop } = useVoiceInput(language, (transcript) =>
    onChange(transcript),
  );

  const large = size === "lg";

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!loading && value.trim()) onSubmit();
      }}
      className={`flex items-center gap-2 rounded-2xl border bg-white shadow-card transition
                  focus-within:border-ink-500 focus-within:ring-4 focus-within:ring-ink-500/10
                  ${large ? "border-ink-200 p-2" : "border-ink-200 p-1.5"}`}
    >
      <Search
        className={`ml-2 shrink-0 text-ink-400 ${large ? "h-5 w-5" : "h-4 w-4"}`}
        aria-hidden
      />

      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? t("hero.placeholder")}
        autoFocus={autoFocus}
        aria-label={placeholder ?? t("hero.placeholder")}
        className={`min-w-0 flex-1 bg-transparent text-ink-950 placeholder:text-ink-400
                    focus:outline-none ${large ? "py-2.5 text-base" : "py-1.5 text-sm"}`}
      />

      {supported && (
        <button
          type="button"
          onClick={listening ? stop : start}
          aria-label={t("hero.voice")}
          aria-pressed={listening}
          className={`shrink-0 rounded-xl p-2.5 transition ${
            listening
              ? "animate-pulse bg-red-50 text-red-600"
              : "text-ink-400 hover:bg-ink-50 hover:text-ink-700"
          }`}
        >
          {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </button>
      )}

      <button
        type="submit"
        disabled={loading || !value.trim()}
        className={`btn-primary shrink-0 ${large ? "!px-5 !py-3" : "!px-4 !py-2"}`}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <>
            <span className={large ? "" : "hidden sm:inline"}>
              {submitLabel ?? t("hero.search")}
            </span>
            <ArrowRight className="h-4 w-4" aria-hidden />
          </>
        )}
      </button>
    </form>
  );
}

// --------------------------------------------------------------------------
// Pipeline trace
// --------------------------------------------------------------------------
const STAGE_LABELS: Record<string, Parameters<ReturnType<typeof useI18n>["t"]>[0]> = {
  intent: "pipeline.intent",
  product: "pipeline.product",
  retrieving: "pipeline.retrieving",
  retrieved: "pipeline.retrieved",
  ranked: "pipeline.ranked",
  composing: "pipeline.composing",
  verified: "pipeline.verified",
};

/**
 * Live view of the retrieval pipeline. The stages are streamed from the backend as they
 * actually complete, so this is a progress report rather than a decorative animation.
 */
export function PipelineTrace({ stages }: { stages: { event: string; data: any }[] }) {
  const { t } = useI18n();
  const visible = stages.filter((s) => s.event in STAGE_LABELS);
  if (!visible.length) return null;

  return (
    <ol className="space-y-2 rounded-xl border border-ink-100 bg-white p-4">
      {visible.map((stage, i) => {
        const last = i === visible.length - 1;
        const detail = describe(stage);
        return (
          <li key={`${stage.event}-${i}`} className="flex items-center gap-3 text-xs">
            {last ? (
              <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-ink-500" aria-hidden />
            ) : (
              <span
                className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-[0.6rem] text-emerald-700"
                aria-hidden
              >
                ✓
              </span>
            )}
            <span className={last ? "font-medium text-ink-900" : "text-ink-500"}>
              {t(STAGE_LABELS[stage.event])}
            </span>
            {detail && <span className="font-mono text-[0.65rem] text-ink-400">{detail}</span>}
          </li>
        );
      })}
    </ol>
  );
}

function describe(stage: { event: string; data: any }): string {
  const d = stage.data ?? {};
  if (stage.event === "intent") return String(d.intent ?? "");
  if (stage.event === "retrieved") return `${d.count ?? 0} passages`;
  if (stage.event === "ranked")
    return Array.isArray(d.standards) ? d.standards.slice(0, 3).join(", ") : "";
  if (stage.event === "composing") return String(d.generator ?? "");
  if (stage.event === "product") return String(d.product?.product ?? "");
  return "";
}

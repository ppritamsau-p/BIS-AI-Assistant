"use client";

import { KeyRound, LogIn, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { ErrorBox } from "@/components/ui";

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await login(username, password);
      window.localStorage.setItem("bis_token", result.access_token);
      window.localStorage.setItem("bis_role", result.role);
      router.push(result.role === "admin" ? "/admin" : "/assistant");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page flex min-h-[70vh] items-center justify-center py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-ink-900 text-white">
            <ShieldCheck className="h-6 w-6" aria-hidden />
          </span>
          <h1 className="mt-4 text-xl font-bold text-ink-950">{t("login.title")}</h1>
          <p className="mt-1.5 text-sm text-ink-600">{t("login.subtitle")}</p>
        </div>

        <form onSubmit={submit} className="card space-y-4 p-6">
          <label className="block">
            <span className="label">{t("login.username")}</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              className="input"
            />
          </label>

          <label className="block">
            <span className="label">{t("login.password")}</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="input"
            />
          </label>

          {error && <ErrorBox message={error} />}

          <button type="submit" disabled={loading} className="btn-primary w-full">
            <LogIn className="h-4 w-4" aria-hidden />
            {t("login.submit")}
          </button>
        </form>

        <div className="mt-4 rounded-xl border border-ink-100 bg-white p-4">
          <p className="flex items-center gap-2 text-xs font-semibold text-ink-700">
            <KeyRound className="h-3.5 w-3.5 text-ink-400" aria-hidden />
            {t("login.demoCredentials")}
          </p>
          <dl className="mt-2.5 space-y-1 font-mono text-xs text-ink-600">
            <div className="flex justify-between">
              <dt>admin</dt>
              <dd>admin123</dd>
            </div>
            <div className="flex justify-between">
              <dt>user</dt>
              <dd>user123</dd>
            </div>
          </dl>
          <p className="mt-3 text-[0.65rem] leading-relaxed text-ink-400">
            Development defaults only. Set ADMIN_PASSWORD and USER_PASSWORD on the backend,
            and move users into the database, before any real deployment.
          </p>
        </div>
      </div>
    </div>
  );
}

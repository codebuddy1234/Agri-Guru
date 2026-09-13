"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { api, ApiClientError, tokenStore } from "@/lib/api-client";
import { translateError } from "@/hooks/use-translated-error";
import { RESULT_STORAGE_KEY } from "./crop-form";
import { PredictionResult } from "./prediction-result";
import { AppHeader } from "@/components/layout/app-header";
import { Alert } from "@/components/ui/alert";
import type { Dictionary } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n.client";
import type { Prediction } from "@/types/api";

function ResultBody({ locale, t }: { locale: Locale; t: Dictionary }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = searchParams.get("id");

  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.access) {
      router.replace(`/${locale}/login`);
      return;
    }
    if (!id) {
      router.replace(`/${locale}/crop-recommendation`);
      return;
    }

    // Prefer the copy the form just handed over; fall back to fetching by id
    // so a shared or reloaded URL still works.
    try {
      const cached = sessionStorage.getItem(RESULT_STORAGE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached) as Prediction;
        if (parsed.id === id) {
          setPrediction(parsed);
          setLoading(false);
          return;
        }
      }
    } catch {
      /* fall through to the fetch */
    }

    let cancelled = false;
    api
      .historyDetail(id)
      .then((p) => {
        if (!cancelled) setPrediction(p);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiClientError && err.status === 401) {
          router.replace(`/${locale}/login`);
          return;
        }
        setError(translateError(err, t.errors, t.common.somethingWentWrong));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id, locale, router, t]);

  if (loading) {
    return <p className="py-10 text-center text-soil-700">{t.common.loading}</p>;
  }
  if (error) {
    return <Alert tone="error">{error}</Alert>;
  }
  if (!prediction) {
    return <Alert tone="error">{t.errors.NOT_FOUND}</Alert>;
  }

  return (
    <>
      <p className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-leaf-100 px-3 py-1.5 text-sm font-semibold text-leaf-800">
        <CheckCircle2 className="h-4 w-4" aria-hidden />
        {t.result.saved}
      </p>
      <PredictionResult prediction={prediction} locale={locale} t={t} />
    </>
  );
}

export function ResultView({ locale, t }: { locale: Locale; t: Dictionary }) {
  return (
    <div className="min-h-screen bg-soil-50">
      <AppHeader
        locale={locale}
        appName={t.common.appName}
        signOutLabel={t.common.signOut}
        profileLabel={t.dashboard.profile}
      />
      <main className="mx-auto max-w-2xl px-4 py-6">
        {/* useSearchParams needs a Suspense boundary during prerender. */}
        <Suspense
          fallback={<p className="py-10 text-center text-soil-700">{t.common.loading}</p>}
        >
          <ResultBody locale={locale} t={t} />
        </Suspense>
      </main>
    </div>
  );
}

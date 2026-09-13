"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { api, ApiClientError, tokenStore } from "@/lib/api-client";
import { translateError } from "@/hooks/use-translated-error";
import { formatDateTime } from "@/lib/format";
import { PredictionResult } from "./prediction-result";
import { AppHeader } from "@/components/layout/app-header";
import { Alert } from "@/components/ui/alert";
import type { Dictionary } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n.client";
import type { Prediction } from "@/types/api";

export function HistoryDetail({
  id,
  locale,
  t,
}: {
  id: string;
  locale: Locale;
  t: Dictionary;
}) {
  const router = useRouter();
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.access) {
      router.replace(`/${locale}/login`);
      return;
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

  return (
    <div className="min-h-screen bg-soil-50">
      <AppHeader
        locale={locale}
        appName={t.common.appName}
        signOutLabel={t.common.signOut}
        profileLabel={t.dashboard.profile}
      />
      <main className="mx-auto max-w-2xl px-4 py-6">
        <Link
          href={`/${locale}/history`}
          className="inline-flex min-h-[44px] items-center gap-1.5 text-sm font-semibold text-leaf-700"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          {t.common.back}
        </Link>

        <h1 className="mt-2 text-2xl font-bold text-soil-900">
          {t.history.detailTitle}
        </h1>
        {prediction && (
          <p className="mt-1 text-sm text-soil-700">
            {t.history.recordedOn} {formatDateTime(prediction.created_at, locale)}
          </p>
        )}

        <div className="mt-5">
          {loading ? (
            <p className="py-10 text-center text-soil-700">{t.common.loading}</p>
          ) : error ? (
            <Alert tone="error">{error}</Alert>
          ) : prediction ? (
            <PredictionResult prediction={prediction} locale={locale} t={t} />
          ) : (
            <Alert tone="error">{t.errors.NOT_FOUND}</Alert>
          )}
        </div>
      </main>
    </div>
  );
}

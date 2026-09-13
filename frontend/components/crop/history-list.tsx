"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight, History as HistoryIcon } from "lucide-react";
import { api, ApiClientError, tokenStore } from "@/lib/api-client";
import { translateError } from "@/hooks/use-translated-error";
import { cropName, formatDateTime, formatPercent } from "@/lib/format";
import { AppHeader } from "@/components/layout/app-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import type { Dictionary } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n.client";
import type { PredictionHistoryItem } from "@/types/api";

const PAGE_SIZE = 20;

export function HistoryList({ locale, t }: { locale: Locale; t: Dictionary }) {
  const router = useRouter();
  const [items, setItems] = useState<PredictionHistoryItem[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(offset: number) {
    const page = await api.history(PAGE_SIZE, offset);
    setItems((prev) => (offset === 0 ? page.data : [...prev, ...page.data]));
    setHasMore(page.meta.has_more);
  }

  useEffect(() => {
    if (!tokenStore.access) {
      router.replace(`/${locale}/login`);
      return;
    }
    load(0)
      .catch((err) => {
        if (err instanceof ApiClientError && err.status === 401) {
          router.replace(`/${locale}/login`);
          return;
        }
        setError(translateError(err, t.errors, t.common.somethingWentWrong));
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale, router]);

  async function loadMore() {
    setLoadingMore(true);
    try {
      await load(items.length);
    } catch (err) {
      setError(translateError(err, t.errors, t.common.somethingWentWrong));
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <div className="min-h-screen bg-soil-50">
      <AppHeader
        locale={locale}
        appName={t.common.appName}
        signOutLabel={t.common.signOut}
        profileLabel={t.dashboard.profile}
      />
      <main className="mx-auto max-w-2xl px-4 py-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-soil-900">
          <HistoryIcon className="h-6 w-6 text-leaf-600" aria-hidden />
          {t.history.title}
        </h1>
        <p className="mt-1 text-soil-700">{t.history.subtitle}</p>

        {error && (
          <Alert tone="error" className="mt-5">
            {error}
          </Alert>
        )}

        {loading ? (
          <p className="py-10 text-center text-soil-700">{t.common.loading}</p>
        ) : items.length === 0 ? (
          <Card className="mt-5">
            <CardContent className="p-8 text-center">
              <p className="text-soil-700">{t.history.empty}</p>
              <Link href={`/${locale}/crop-recommendation`} className="mt-4 inline-block">
                <Button>{t.history.emptyAction}</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <>
            <Card className="mt-5">
              <CardContent className="p-0">
                <ul className="divide-y divide-leaf-100">
                  {items.map((item) => (
                    <li key={item.id}>
                      <Link
                        href={`/${locale}/history/${item.id}`}
                        className="flex min-h-[68px] items-center gap-3 px-5 py-3 hover:bg-leaf-50"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-soil-900">
                            {cropName(t, item.recommended_crop)}
                          </p>
                          <p className="text-sm text-soil-700">
                            {formatDateTime(item.created_at, locale)}
                          </p>
                        </div>
                        {item.confidence !== null && (
                          <span className="shrink-0 rounded-full bg-leaf-100 px-3 py-1 text-sm font-semibold text-leaf-800">
                            {formatPercent(item.confidence, locale)}
                          </span>
                        )}
                        <ChevronRight
                          className="h-5 w-5 shrink-0 text-soil-700/50"
                          aria-hidden
                        />
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {hasMore && (
              <Button
                variant="outline"
                className="mt-4 w-full"
                loading={loadingMore}
                onClick={loadMore}
              >
                {t.history.loadMore}
              </Button>
            )}
          </>
        )}
      </main>
    </div>
  );
}

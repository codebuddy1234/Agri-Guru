"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MapPin } from "lucide-react";
import { api, ApiClientError, tokenStore } from "@/lib/api-client";
import { translateError } from "@/hooks/use-translated-error";
import { interpolate, cropName, formatDate } from "@/lib/format";
import { AppHeader } from "@/components/layout/app-header";
import { ModuleCard } from "@/components/layout/module-card";
import { Card, CardContent } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import type { Dictionary } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n.client";
import type { FarmerProfile, PlatformModule, PredictionHistoryItem } from "@/types/api";

export function DashboardView({ locale, t }: { locale: Locale; t: Dictionary }) {
  const router = useRouter();
  const [profile, setProfile] = useState<FarmerProfile | null>(null);
  const [modules, setModules] = useState<PlatformModule[]>([]);
  const [recent, setRecent] = useState<PredictionHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.access) {
      router.replace(`/${locale}/login`);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        // Fetched together: three sequential round trips is a visible delay
        // on a slow rural connection.
        const [p, m, h] = await Promise.all([
          api.getProfile(),
          api.modules(),
          api.history(3, 0),
        ]);
        if (cancelled) return;
        setProfile(p);
        setModules(m);
        setRecent(h.data);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiClientError && err.status === 401) {
          router.replace(`/${locale}/login`);
          return;
        }
        setError(translateError(err, t.errors, t.common.somethingWentWrong));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [locale, router, t]);

  const location =
    [profile?.village, profile?.taluka, profile?.district].filter(Boolean).join(", ") ||
    t.dashboard.locationNotSet;

  const moduleStrings = t.modules as Record<string, { title: string; description: string }>;

  return (
    <div className="min-h-screen bg-soil-50">
      <AppHeader
        locale={locale}
        appName={t.common.appName}
        signOutLabel={t.common.signOut}
        profileLabel={t.dashboard.profile}
      />

      <main className="mx-auto max-w-5xl px-4 py-6">
        <section className="animate-fade-up">
          <h1 className="text-2xl font-bold text-soil-900 sm:text-3xl">
            {profile?.full_name
              ? interpolate(t.dashboard.greeting, { name: profile.full_name })
              : t.dashboard.greetingNoName}
          </h1>
          <p className="mt-1 text-soil-700">{t.dashboard.subtitle}</p>
          <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-soil-700">
            <MapPin className="h-4 w-4 text-leaf-600" aria-hidden />
            {loading ? t.common.loading : location}
          </p>
        </section>

        {error && (
          <Alert tone="error" className="mt-5">
            {error}
          </Alert>
        )}

        <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((m) => (
            <ModuleCard
              key={m.key}
              module={m}
              locale={locale}
              title={moduleStrings[m.key]?.title ?? m.key}
              description={moduleStrings[m.key]?.description ?? ""}
              availableLabel={t.common.availableNow}
              comingSoonLabel={t.common.comingSoon}
            />
          ))}
        </section>

        <section className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-soil-900">{t.dashboard.recentTitle}</h2>
            {recent.length > 0 && (
              <Link
                href={`/${locale}/history`}
                className="text-sm font-semibold text-leaf-700 underline"
              >
                {t.dashboard.viewAll}
              </Link>
            )}
          </div>

          <Card className="mt-3">
            <CardContent className="p-0">
              {loading ? (
                <p className="p-5 text-sm text-soil-700">{t.common.loading}</p>
              ) : recent.length === 0 ? (
                <p className="p-5 text-sm text-soil-700">{t.dashboard.recentEmpty}</p>
              ) : (
                <ul className="divide-y divide-leaf-100">
                  {recent.map((item) => (
                    <li key={item.id}>
                      <Link
                        href={`/${locale}/history/${item.id}`}
                        className="flex min-h-[60px] items-center justify-between gap-3 px-5 py-3 hover:bg-leaf-50"
                      >
                        <span className="font-semibold text-soil-900">
                          {cropName(t, item.recommended_crop)}
                        </span>
                        <span className="text-sm text-soil-700">
                          {formatDate(item.created_at, locale)}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

import Link from "next/link";
import { Sprout, ClipboardList, Search, History } from "lucide-react";
import { getDictionary, isLocale, type Locale } from "@/lib/i18n";
import { notFound } from "next/navigation";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { Card, CardContent } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";

export default async function LandingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getDictionary(locale as Locale);

  const steps = [
    { icon: ClipboardList, title: t.landing.step1Title, body: t.landing.step1Body },
    { icon: Search, title: t.landing.step2Title, body: t.landing.step2Body },
    { icon: History, title: t.landing.step3Title, body: t.landing.step3Body },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-leaf-50 via-soil-50 to-soil-50">
      <header className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-4">
        <span className="flex items-center gap-2 text-lg font-bold text-leaf-700">
          <Sprout className="h-6 w-6" aria-hidden />
          {t.common.appName}
        </span>
        <div className="ml-auto">
          <LanguageSwitcher current={locale as Locale} />
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-16">
        <section className="animate-fade-up py-8 sm:py-14">
          <h1 className="max-w-2xl text-3xl font-bold leading-tight text-soil-900 sm:text-5xl">
            {t.landing.heroTitle}
          </h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-soil-700 sm:text-lg">
            {t.landing.heroSubtitle}
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href={`/${locale}/register`}
              className="inline-flex min-h-[56px] items-center justify-center rounded-xl bg-leaf-600 px-8 text-lg font-semibold text-white transition-colors hover:bg-leaf-700"
            >
              {t.landing.getStarted}
            </Link>
            <Link
              href={`/${locale}/login`}
              className="inline-flex min-h-[56px] items-center justify-center rounded-xl border-2 border-leaf-600 bg-white px-8 text-lg font-semibold text-leaf-700 transition-colors hover:bg-leaf-50"
            >
              {t.landing.haveAccount}
            </Link>
          </div>
        </section>

        <section className="py-8">
          <h2 className="text-2xl font-bold text-soil-900">
            {t.landing.howItWorksTitle}
          </h2>
          <ol className="mt-6 grid gap-4 sm:grid-cols-3">
            {steps.map((step, i) => (
              <li key={step.title}>
                <Card className="h-full">
                  <CardContent className="p-5">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-leaf-100 text-leaf-700">
                      <step.icon className="h-5 w-5" aria-hidden />
                    </div>
                    <p className="mt-3 text-xs font-bold uppercase tracking-wide text-leaf-600">
                      {i + 1}
                    </p>
                    <h3 className="mt-1 font-bold text-soil-900">{step.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-soil-700">
                      {step.body}
                    </p>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ol>
        </section>

        {/* Stated up front, not buried in a footer: a farmer should know what
            this tool does and does not know before they rely on it. */}
        <section className="pt-6">
          <Alert tone="warning" title={t.landing.honestyTitle}>
            <p className="mt-1">{t.landing.honestyBody}</p>
          </Alert>
        </section>
      </main>
    </div>
  );
}

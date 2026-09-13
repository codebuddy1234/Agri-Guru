import { notFound } from "next/navigation";
import { isLocale, locales } from "@/lib/i18n";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();

  // lang is set here rather than in the root layout: it is what makes the
  // Devanagari line-height rule and screen-reader pronunciation correct.
  return (
    <div lang={locale} className="min-h-screen">
      {children}
    </div>
  );
}

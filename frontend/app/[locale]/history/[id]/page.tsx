import { notFound } from "next/navigation";
import { getDictionary, isLocale, type Locale } from "@/lib/i18n";
import { HistoryDetail } from "@/components/crop/history-detail";

export default async function HistoryDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getDictionary(locale as Locale);
  return <HistoryDetail id={id} locale={locale as Locale} t={t} />;
}

import { notFound } from "next/navigation";
import { getDictionary, isLocale, type Locale } from "@/lib/i18n";
import { CropForm } from "@/components/crop/crop-form";

export default async function CropRecommendationPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getDictionary(locale as Locale);
  return <CropForm locale={locale as Locale} t={t} />;
}

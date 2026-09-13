"use client";

import Link from "next/link";
import { Sprout } from "lucide-react";
import { cropName, formatPercent, interpolate } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { Dictionary } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n.client";
import type { Prediction } from "@/types/api";

/**
 * Confidence bands.
 *
 * The model reports a real probability (the fraction of trees that voted for
 * the top crop), so the number itself is not invented. What it means is a
 * different question, and a bare "95%" reads as "95% chance this crop will
 * succeed", which is not what it measures. Each band therefore comes with a
 * sentence describing what the model actually did.
 */
function confidenceBand(confidence: number): "high" | "medium" | "low" {
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.55) return "medium";
  return "low";
}

const bandStyles = {
  high: "bg-leaf-600",
  medium: "bg-harvest-400",
  low: "bg-soil-700/60",
} as const;

export function PredictionResult({
  prediction,
  locale,
  t,
}: {
  prediction: Prediction;
  locale: Locale;
  t: Dictionary;
}) {
  const confidence = prediction.confidence;
  const band = confidence !== null ? confidenceBand(confidence) : null;
  const bandText =
    band === "high"
      ? t.result.confidenceHigh
      : band === "medium"
        ? t.result.confidenceMedium
        : band === "low"
          ? t.result.confidenceLow
          : null;

  const inputs = prediction.inputs;

  return (
    <div className="space-y-5">
      {/* --- The recommendation --- */}
      <Card className="animate-fade-up overflow-hidden">
        <div className="bg-gradient-to-br from-leaf-600 to-leaf-700 px-6 py-8 text-center text-white">
          <Sprout className="mx-auto h-10 w-10 opacity-90" aria-hidden />
          <p className="mt-2 text-sm font-semibold uppercase tracking-wide opacity-90">
            {t.result.title}
          </p>
          <p className="mt-1 text-4xl font-bold">
            {cropName(t, prediction.recommended_crop)}
          </p>
        </div>

        {confidence !== null && band && (
          <CardContent className="p-5">
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-semibold text-soil-900">
                {t.result.confidence}
              </span>
              <span className="text-2xl font-bold text-soil-900">
                {formatPercent(confidence, locale)}
              </span>
            </div>
            <div
              role="meter"
              aria-valuenow={Math.round(confidence * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={t.result.confidence}
              className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-leaf-100"
            >
              <div
                className={`h-full rounded-full transition-all ${bandStyles[band]}`}
                style={{ width: `${Math.max(confidence * 100, 2)}%` }}
              />
            </div>
            <p className="mt-2 text-sm leading-relaxed text-soil-700">{bandText}</p>
          </CardContent>
        )}
      </Card>

      {/* --- Extrapolation warning, when it applies --- */}
      {prediction.out_of_training_range.length > 0 && (
        <Alert tone="warning" title={t.result.outOfRangeTitle}>
          <p className="mt-1">
            {interpolate(t.result.outOfRangeBody, {
              fields: prediction.out_of_training_range
                .map((f) => {
                  const crop = t.crop as Record<string, string>;
                  return crop[f] ?? f;
                })
                .join(", "),
            })}
          </p>
        </Alert>
      )}

      {/* --- Alternatives: the honest framing of a single-answer model --- */}
      <Card>
        <CardContent className="p-5">
          <h2 className="font-bold text-soil-900">{t.result.alternativesTitle}</h2>
          {prediction.alternatives.length === 0 ? (
            <p className="mt-2 text-sm text-soil-700">{t.result.noAlternatives}</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {prediction.alternatives.map((alt) => (
                <li
                  key={alt.crop}
                  className="flex items-center justify-between rounded-xl bg-leaf-50 px-4 py-3"
                >
                  <span className="font-semibold text-soil-900">
                    {cropName(t, alt.crop)}
                  </span>
                  <span className="text-sm font-medium text-soil-700">
                    {formatPercent(alt.probability, locale)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* --- Why: restates the farmer's own inputs, invents nothing --- */}
      <Card>
        <CardContent className="p-5">
          <h2 className="font-bold text-soil-900">{t.result.whyTitle}</h2>
          <p className="mt-2 text-sm leading-relaxed text-soil-700">
            {interpolate(t.result.whyBody, {
              nitrogen: inputs.nitrogen ?? "-",
              phosphorus: inputs.phosphorus ?? "-",
              potassium: inputs.potassium ?? "-",
              temperature: inputs.temperature ?? "-",
              humidity: inputs.humidity ?? "-",
              ph: inputs.ph ?? "-",
              rainfall: inputs.rainfall ?? "-",
              crop: cropName(t, prediction.recommended_crop),
            })}
          </p>

          <h3 className="mt-4 text-sm font-bold text-soil-900">
            {t.result.yourInputs}
          </h3>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
            {(
              [
                ["nitrogen", ""],
                ["phosphorus", ""],
                ["potassium", ""],
                ["temperature", "°C"],
                ["humidity", "%"],
                ["ph", ""],
                ["rainfall", "mm"],
              ] as const
            ).map(([key, unit]) => (
              <div key={key}>
                <dt className="text-soil-700">
                  {(t.crop as Record<string, string>)[key]}
                </dt>
                <dd className="font-semibold text-soil-900">
                  {inputs[key] ?? "-"}
                  {unit && ` ${unit}`}
                </dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      {/* --- The disclaimer a farmer must see before acting on this --- */}
      <Alert tone="warning" title={t.result.disclaimerTitle}>
        <p className="mt-1">{t.result.disclaimerBody}</p>
      </Alert>

      <p className="text-center text-xs text-soil-700/70">
        {interpolate(t.result.modelInfo, {
          version: prediction.model_version,
          algorithm: prediction.model_name,
        })}
      </p>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link href={`/${locale}/crop-recommendation`} className="flex-1">
          <Button variant="primary" size="lg" className="w-full">
            {t.result.newRecommendation}
          </Button>
        </Link>
        <Link href={`/${locale}/history`} className="flex-1">
          <Button variant="outline" size="lg" className="w-full">
            {t.result.viewHistory}
          </Button>
        </Link>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sprout } from "lucide-react";
import { api, ApiClientError, tokenStore } from "@/lib/api-client";
import { translateError } from "@/hooks/use-translated-error";
import { interpolate } from "@/lib/format";
import {
  CROP_FIELDS,
  EMPTY_CROP_FORM,
  validateCropForm,
  type CropFormValues,
} from "@/lib/crop-fields";
import { AppHeader } from "@/components/layout/app-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { NumberField } from "@/components/ui/field";
import { Alert } from "@/components/ui/alert";
import type { Dictionary } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n.client";
import type { Farm } from "@/types/api";

/** Where a completed prediction is handed to the result page. */
export const RESULT_STORAGE_KEY = "agriguru.last_prediction";

export function CropForm({ locale, t }: { locale: Locale; t: Dictionary }) {
  const router = useRouter();
  const [values, setValues] = useState<CropFormValues>(EMPTY_CROP_FORM);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [farmId, setFarmId] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!tokenStore.access) {
      router.replace(`/${locale}/login`);
      return;
    }
    // Farms are optional; a failure here must not block the form.
    api.listFarms().then(setFarms).catch(() => setFarms([]));
  }, [locale, router]);

  const set = (name: keyof CropFormValues) => (value: string) => {
    setValues((v) => ({ ...v, [name]: value }));
    setFieldErrors((e) => {
      if (!(name in e)) return e;
      const { [name]: _removed, ...rest } = e;
      return rest;
    });
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const clientErrors = validateCropForm(values, {
      required: t.errors.INVALID_INPUT,
      range: (min, max) =>
        interpolate(t.crop.acceptedRange, { min, max }),
    });
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      // Move focus to the first problem so a farmer on a phone is not left
      // scrolling to find what went wrong.
      const first = CROP_FIELDS.find((f) => clientErrors[f.name]);
      if (first) document.getElementById(first.name)?.focus();
      return;
    }

    setSubmitting(true);
    try {
      const prediction = await api.predict({
        nitrogen: Number(values.nitrogen),
        phosphorus: Number(values.phosphorus),
        potassium: Number(values.potassium),
        temperature: Number(values.temperature),
        humidity: Number(values.humidity),
        ph: Number(values.ph),
        rainfall: Number(values.rainfall),
        farm_id: farmId || null,
      });

      // Hand the result to the result page through sessionStorage rather than
      // the URL: the prediction is already saved server-side, and this avoids
      // a long query string or an immediate second fetch.
      try {
        sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(prediction));
      } catch {
        /* storage blocked: the result page falls back to fetching by id */
      }
      router.push(`/${locale}/crop-recommendation/result?id=${prediction.id}`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setFieldErrors(err.fieldErrors());
        if (err.status === 401) {
          router.replace(`/${locale}/login`);
          return;
        }
      }
      setError(translateError(err, t.errors, t.common.somethingWentWrong));
      setSubmitting(false);
    }
  }

  const soilFields = CROP_FIELDS.filter((f) => f.section === "soil");
  const weatherFields = CROP_FIELDS.filter((f) => f.section === "weather");

  const renderField = (field: (typeof CROP_FIELDS)[number]) => (
    <NumberField
      key={field.name}
      id={field.name}
      label={t.crop[field.labelKey]}
      help={t.crop[field.helpKey]}
      hint={interpolate(t.crop.acceptedRange, { min: field.min, max: field.max })}
      unit={field.unit}
      min={field.min}
      max={field.max}
      step={field.step}
      value={values[field.name]}
      onChange={set(field.name)}
      error={fieldErrors[field.name]}
      required
    />
  );

  return (
    <div className="min-h-screen bg-soil-50">
      <AppHeader
        locale={locale}
        appName={t.common.appName}
        signOutLabel={t.common.signOut}
        profileLabel={t.dashboard.profile}
      />

      <main className="mx-auto max-w-2xl px-4 py-6">
        <div className="animate-fade-up">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-soil-900">
            <Sprout className="h-7 w-7 text-leaf-600" aria-hidden />
            {t.crop.title}
          </h1>
          <p className="mt-1 text-soil-700">{t.crop.subtitle}</p>
        </div>

        {error && (
          <Alert tone="error" className="mt-5">
            {error}
          </Alert>
        )}

        <form onSubmit={onSubmit} className="mt-5 space-y-5" noValidate>
          <Card>
            <CardContent className="space-y-5 p-5">
              <h2 className="text-lg font-bold text-soil-900">{t.crop.soilSection}</h2>

              {/* The unit warning sits above the N/P/K inputs, not in a
                  footnote: a farmer copying kg/ha from a soil health card
                  needs to see this before they type, not after. */}
              <Alert tone="warning" title={t.crop.npkUnitWarningTitle}>
                <p className="mt-1">{t.crop.npkUnitWarningBody}</p>
              </Alert>

              <div className="grid gap-5 sm:grid-cols-2">
                {soilFields.map(renderField)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-5 p-5">
              <h2 className="text-lg font-bold text-soil-900">{t.crop.weatherSection}</h2>
              <div className="grid gap-5 sm:grid-cols-2">
                {weatherFields.map(renderField)}
              </div>
            </CardContent>
          </Card>

          {farms.length > 0 && (
            <Card>
              <CardContent className="p-5">
                <label
                  htmlFor="farm_id"
                  className="block text-sm font-semibold text-soil-900"
                >
                  {t.crop.linkFarm}
                </label>
                <select
                  id="farm_id"
                  value={farmId}
                  onChange={(e) => setFarmId(e.target.value)}
                  className="mt-2 min-h-[52px] w-full rounded-xl border-2 border-leaf-200 bg-white px-4 text-base text-soil-900 focus:border-leaf-500 focus:outline-none focus:ring-2 focus:ring-leaf-400"
                >
                  <option value="">{t.crop.noFarm}</option>
                  {farms.map((farm) => (
                    <option key={farm.id} value={farm.id}>
                      {farm.name} — {farm.area_value} {farm.area_unit}
                    </option>
                  ))}
                </select>
              </CardContent>
            </Card>
          )}

          <Button type="submit" size="lg" loading={submitting} className="w-full">
            {submitting ? t.crop.submitting : t.crop.submit}
          </Button>
        </form>
      </main>
    </div>
  );
}

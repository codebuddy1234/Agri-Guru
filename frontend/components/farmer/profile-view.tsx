"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiClientError, tokenStore } from "@/lib/api-client";
import { translateError } from "@/hooks/use-translated-error";
import { AppHeader } from "@/components/layout/app-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { TextField } from "@/components/ui/field";
import { Alert } from "@/components/ui/alert";
import { localeNames, locales, type Locale } from "@/lib/i18n.client";
import type { Dictionary } from "@/lib/i18n";
import type { Farm, FarmerProfile } from "@/types/api";

export function ProfileView({ locale, t }: { locale: Locale; t: Dictionary }) {
  const router = useRouter();
  const [profile, setProfile] = useState<FarmerProfile | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [form, setForm] = useState({
    full_name: "",
    district: "",
    taluka: "",
    village: "",
    pincode: "",
    preferred_language: locale as string,
  });
  const [newFarm, setNewFarm] = useState({ name: "", area_value: "", area_unit: "acre" });
  const [showFarmForm, setShowFarmForm] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.access) {
      router.replace(`/${locale}/login`);
      return;
    }
    Promise.all([api.getProfile(), api.listFarms()])
      .then(([p, f]) => {
        setProfile(p);
        setFarms(f);
        setForm({
          full_name: p.full_name ?? "",
          district: p.district ?? "",
          taluka: p.taluka ?? "",
          village: p.village ?? "",
          pincode: p.pincode ?? "",
          preferred_language: p.preferred_language,
        });
      })
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

  const set = (key: keyof typeof form) => (value: string) => {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  };

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      // Empty strings are sent as null so clearing a field actually clears it,
      // rather than storing "".
      const updated = await api.updateProfile({
        full_name: form.full_name,
        district: form.district || null,
        taluka: form.taluka || null,
        village: form.village || null,
        pincode: form.pincode || null,
        preferred_language: form.preferred_language,
      } as never);
      setProfile(updated);
      setSaved(true);
      // The language choice is part of this form, so honour it immediately.
      if (updated.preferred_language !== locale) {
        router.push(`/${updated.preferred_language}/profile`);
      }
    } catch (err) {
      if (err instanceof ApiClientError) setFieldErrors(err.fieldErrors());
      setError(translateError(err, t.errors, t.common.somethingWentWrong));
    } finally {
      setSaving(false);
    }
  }

  async function addFarm(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const farm = await api.createFarm({
        name: newFarm.name,
        area_value: Number(newFarm.area_value),
        area_unit: newFarm.area_unit,
      });
      setFarms((prev) => [farm, ...prev]);
      setNewFarm({ name: "", area_value: "", area_unit: "acre" });
      setShowFarmForm(false);
    } catch (err) {
      setError(translateError(err, t.errors, t.common.somethingWentWrong));
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
        <h1 className="text-2xl font-bold text-soil-900">{t.profile.title}</h1>
        <p className="mt-1 text-soil-700">{t.profile.subtitle}</p>

        {error && (
          <Alert tone="error" className="mt-5">
            {error}
          </Alert>
        )}
        {saved && (
          <Alert tone="success" className="mt-5">
            {t.profile.updated}
          </Alert>
        )}

        {loading ? (
          <p className="py-10 text-center text-soil-700">{t.common.loading}</p>
        ) : (
          <>
            <form onSubmit={saveProfile} className="mt-5 space-y-5" noValidate>
              <Card>
                <CardContent className="space-y-4 p-5">
                  <h2 className="font-bold text-soil-900">{t.profile.personalSection}</h2>
                  <TextField
                    id="full_name"
                    label={t.auth.fullName}
                    value={form.full_name}
                    onChange={set("full_name")}
                    error={fieldErrors.full_name}
                    required
                  />
                </CardContent>
              </Card>

              <Card>
                <CardContent className="space-y-4 p-5">
                  <h2 className="font-bold text-soil-900">{t.profile.locationSection}</h2>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      id="district"
                      label={t.auth.district}
                      value={form.district}
                      onChange={set("district")}
                      error={fieldErrors.district}
                    />
                    <TextField
                      id="taluka"
                      label={t.auth.taluka}
                      value={form.taluka}
                      onChange={set("taluka")}
                      error={fieldErrors.taluka}
                    />
                    <TextField
                      id="village"
                      label={t.auth.village}
                      value={form.village}
                      onChange={set("village")}
                      error={fieldErrors.village}
                    />
                    <TextField
                      id="pincode"
                      label="PIN"
                      inputMode="numeric"
                      value={form.pincode}
                      onChange={set("pincode")}
                      error={fieldErrors.pincode}
                    />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="space-y-3 p-5">
                  <h2 className="font-bold text-soil-900">{t.profile.languageSection}</h2>
                  <div className="flex flex-wrap gap-2">
                    {locales.map((code) => (
                      <button
                        key={code}
                        type="button"
                        onClick={() => set("preferred_language")(code)}
                        aria-pressed={form.preferred_language === code}
                        className={`min-h-[48px] rounded-xl border-2 px-5 font-semibold transition-colors ${
                          form.preferred_language === code
                            ? "border-leaf-600 bg-leaf-600 text-white"
                            : "border-leaf-200 bg-white text-soil-900 hover:bg-leaf-50"
                        }`}
                      >
                        {localeNames[code]}
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Button type="submit" size="lg" loading={saving} className="w-full">
                {t.common.save}
              </Button>
            </form>

            <Card className="mt-5">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <h2 className="font-bold text-soil-900">{t.profile.farmsSection}</h2>
                  {!showFarmForm && (
                    <Button size="sm" variant="outline" onClick={() => setShowFarmForm(true)}>
                      {t.profile.addFarm}
                    </Button>
                  )}
                </div>

                {farms.length === 0 && !showFarmForm && (
                  <p className="mt-3 text-sm text-soil-700">{t.profile.noFarms}</p>
                )}

                {farms.length > 0 && (
                  <ul className="mt-3 space-y-2">
                    {farms.map((farm) => (
                      <li
                        key={farm.id}
                        className="flex items-center justify-between rounded-xl bg-leaf-50 px-4 py-3"
                      >
                        <span className="font-semibold text-soil-900">{farm.name}</span>
                        <span className="text-sm text-soil-700">
                          {farm.area_value} {farm.area_unit}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                {showFarmForm && (
                  <form onSubmit={addFarm} className="mt-4 space-y-4" noValidate>
                    <TextField
                      id="farm_name"
                      label={t.profile.farmName}
                      value={newFarm.name}
                      onChange={(v) => setNewFarm((f) => ({ ...f, name: v }))}
                      required
                    />
                    <div className="grid grid-cols-2 gap-3">
                      <TextField
                        id="farm_area"
                        label={t.profile.farmArea}
                        type="number"
                        inputMode="decimal"
                        step="0.01"
                        value={newFarm.area_value}
                        onChange={(v) => setNewFarm((f) => ({ ...f, area_value: v }))}
                        required
                      />
                      <div className="space-y-1.5">
                        <label
                          htmlFor="area_unit"
                          className="block text-sm font-semibold text-soil-900"
                        >
                          &nbsp;
                        </label>
                        <select
                          id="area_unit"
                          value={newFarm.area_unit}
                          onChange={(e) =>
                            setNewFarm((f) => ({ ...f, area_unit: e.target.value }))
                          }
                          className="min-h-[52px] w-full rounded-xl border-2 border-leaf-200 bg-white px-4 text-base text-soil-900 focus:border-leaf-500 focus:outline-none focus:ring-2 focus:ring-leaf-400"
                        >
                          <option value="acre">acre</option>
                          <option value="guntha">guntha</option>
                          <option value="hectare">hectare</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <Button type="submit" className="flex-1">
                        {t.common.save}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => setShowFarmForm(false)}
                      >
                        {t.common.cancel}
                      </Button>
                    </div>
                  </form>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}

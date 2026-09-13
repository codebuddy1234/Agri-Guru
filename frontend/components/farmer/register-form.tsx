"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiClientError } from "@/lib/api-client";
import { translateError } from "@/hooks/use-translated-error";
import { AppHeader } from "@/components/layout/app-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { TextField } from "@/components/ui/field";
import { Alert } from "@/components/ui/alert";
import type { Locale } from "@/lib/i18n.client";

export interface RegisterStrings {
  appName: string;
  title: string;
  subtitle: string;
  fullName: string;
  email: string;
  password: string;
  passwordHint: string;
  mobile: string;
  district: string;
  taluka: string;
  optional: string;
  submit: string;
  submitting: string;
  hasAccount: string;
  signIn: string;
  signOut: string;
  profile: string;
  errors: Record<string, string>;
  fallbackError: string;
}

export function RegisterForm({
  locale,
  strings,
}: {
  locale: Locale;
  strings: RegisterStrings;
}) {
  const router = useRouter();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    mobile: "",
    district: "",
    taluka: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const set = (key: keyof typeof form) => (value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setLoading(true);
    try {
      await api.register({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        // Send undefined, not "", for optional fields: the backend treats an
        // empty string as a value to validate and would reject it.
        mobile: form.mobile || undefined,
        district: form.district || undefined,
        taluka: form.taluka || undefined,
        preferred_language: locale,
      });
      router.push(`/${locale}/dashboard`);
    } catch (err) {
      if (err instanceof ApiClientError) setFieldErrors(err.fieldErrors());
      setError(translateError(err, strings.errors, strings.fallbackError));
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-soil-50">
      <AppHeader
        locale={locale}
        appName={strings.appName}
        signOutLabel={strings.signOut}
        profileLabel={strings.profile}
        showAccount={false}
      />
      <main className="mx-auto max-w-md px-4 py-8">
        <Card className="animate-fade-up">
          <CardContent className="p-6">
            <h1 className="text-2xl font-bold text-soil-900">{strings.title}</h1>
            <p className="mt-1 text-sm text-soil-700">{strings.subtitle}</p>

            {error && (
              <Alert tone="error" className="mt-5">
                {error}
              </Alert>
            )}

            <form onSubmit={onSubmit} className="mt-5 space-y-4" noValidate>
              <TextField
                id="full_name"
                label={strings.fullName}
                autoComplete="name"
                value={form.full_name}
                onChange={set("full_name")}
                error={fieldErrors.full_name}
                required
              />
              <TextField
                id="email"
                type="email"
                autoComplete="email"
                label={strings.email}
                value={form.email}
                onChange={set("email")}
                error={fieldErrors.email}
                required
              />
              <TextField
                id="password"
                type="password"
                autoComplete="new-password"
                label={strings.password}
                help={strings.passwordHint}
                value={form.password}
                onChange={set("password")}
                error={fieldErrors.password}
                required
              />
              <TextField
                id="mobile"
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                label={`${strings.mobile} (${strings.optional})`}
                value={form.mobile}
                onChange={set("mobile")}
                error={fieldErrors.mobile}
              />
              <div className="grid grid-cols-2 gap-3">
                <TextField
                  id="district"
                  label={`${strings.district} (${strings.optional})`}
                  value={form.district}
                  onChange={set("district")}
                  error={fieldErrors.district}
                />
                <TextField
                  id="taluka"
                  label={`${strings.taluka} (${strings.optional})`}
                  value={form.taluka}
                  onChange={set("taluka")}
                  error={fieldErrors.taluka}
                />
              </div>
              <Button type="submit" size="lg" loading={loading} className="w-full">
                {loading ? strings.submitting : strings.submit}
              </Button>
            </form>

            <p className="mt-6 text-center text-sm text-soil-700">
              {strings.hasAccount}{" "}
              <Link
                href={`/${locale}/login`}
                className="font-semibold text-leaf-700 underline"
              >
                {strings.signIn}
              </Link>
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

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

export interface LoginStrings {
  appName: string;
  title: string;
  subtitle: string;
  email: string;
  password: string;
  submit: string;
  submitting: string;
  noAccount: string;
  register: string;
  signOut: string;
  profile: string;
  errors: Record<string, string>;
  fallbackError: string;
}

export function LoginForm({ locale, strings }: { locale: Locale; strings: LoginStrings }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setLoading(true);
    try {
      const result = await api.login(email, password);
      // Send the farmer to their own preferred language, not whichever
      // locale the login page happened to be served in.
      const preferred = result.profile?.preferred_language ?? locale;
      router.push(`/${preferred}/dashboard`);
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
                id="email"
                type="email"
                autoComplete="email"
                label={strings.email}
                value={email}
                onChange={setEmail}
                error={fieldErrors.email}
                required
              />
              <TextField
                id="password"
                type="password"
                autoComplete="current-password"
                label={strings.password}
                value={password}
                onChange={setPassword}
                error={fieldErrors.password}
                required
              />
              <Button type="submit" size="lg" loading={loading} className="w-full">
                {loading ? strings.submitting : strings.submit}
              </Button>
            </form>

            <p className="mt-6 text-center text-sm text-soil-700">
              {strings.noAccount}{" "}
              <Link
                href={`/${locale}/register`}
                className="font-semibold text-leaf-700 underline"
              >
                {strings.register}
              </Link>
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

import { notFound } from "next/navigation";
import { getDictionary, isLocale, type Locale } from "@/lib/i18n";
import { LoginForm } from "@/components/farmer/login-form";

export default async function LoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getDictionary(locale as Locale);

  return (
    <LoginForm
      locale={locale as Locale}
      strings={{
        appName: t.common.appName,
        title: t.auth.loginTitle,
        subtitle: t.auth.loginSubtitle,
        email: t.auth.email,
        password: t.auth.password,
        submit: t.common.signIn,
        submitting: t.auth.signingIn,
        noAccount: t.auth.noAccount,
        register: t.common.register,
        signOut: t.common.signOut,
        profile: t.dashboard.profile,
        errors: t.errors,
        fallbackError: t.common.somethingWentWrong,
      }}
    />
  );
}

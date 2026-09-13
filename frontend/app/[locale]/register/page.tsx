import { notFound } from "next/navigation";
import { getDictionary, isLocale, type Locale } from "@/lib/i18n";
import { RegisterForm } from "@/components/farmer/register-form";

export default async function RegisterPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getDictionary(locale as Locale);

  return (
    <RegisterForm
      locale={locale as Locale}
      strings={{
        appName: t.common.appName,
        title: t.auth.registerTitle,
        subtitle: t.auth.registerSubtitle,
        fullName: t.auth.fullName,
        email: t.auth.email,
        password: t.auth.password,
        passwordHint: t.auth.passwordHint,
        mobile: t.auth.mobile,
        district: t.auth.district,
        taluka: t.auth.taluka,
        optional: t.common.optional,
        submit: t.common.register,
        submitting: t.auth.creating,
        hasAccount: t.auth.hasAccount,
        signIn: t.common.signIn,
        signOut: t.common.signOut,
        profile: t.dashboard.profile,
        errors: t.errors,
        fallbackError: t.common.somethingWentWrong,
      }}
    />
  );
}

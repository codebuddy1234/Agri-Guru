"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Sprout, User as UserIcon } from "lucide-react";
import { LanguageSwitcher } from "./language-switcher";
import { api } from "@/lib/api-client";
import type { Locale } from "@/lib/i18n.client";

export function AppHeader({
  locale,
  appName,
  signOutLabel,
  profileLabel,
  showAccount = true,
}: {
  locale: Locale;
  appName: string;
  signOutLabel: string;
  profileLabel: string;
  showAccount?: boolean;
}) {
  const router = useRouter();

  function signOut() {
    api.logout();
    router.push(`/${locale}`);
  }

  return (
    <header className="sticky top-0 z-20 border-b border-leaf-100 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
        <Link
          href={`/${locale}${showAccount ? "/dashboard" : ""}`}
          className="flex items-center gap-2 font-bold text-leaf-700"
        >
          <Sprout className="h-6 w-6" aria-hidden />
          <span className="text-lg">{appName}</span>
        </Link>

        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitcher current={locale} />
          {showAccount && (
            <>
              <Link
                href={`/${locale}/profile`}
                aria-label={profileLabel}
                className="flex min-h-[40px] min-w-[40px] items-center justify-center rounded-full text-soil-700 hover:bg-leaf-50"
              >
                <UserIcon className="h-5 w-5" aria-hidden />
              </Link>
              <button
                type="button"
                onClick={signOut}
                aria-label={signOutLabel}
                className="flex min-h-[40px] min-w-[40px] items-center justify-center rounded-full text-soil-700 hover:bg-leaf-50"
              >
                <LogOut className="h-5 w-5" aria-hidden />
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Globe } from "lucide-react";
import { Suspense, useTransition } from "react";
import { locales, localeNames, type Locale } from "@/lib/i18n.client";
import { api, tokenStore } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/**
 * Switching language rewrites the locale segment of the current URL, so the
 * farmer stays on the page they were reading.
 *
 * For a signed-in farmer the choice is also persisted to their profile, so it
 * follows them to another device. That write is fire-and-forget: a failed
 * preference save must not block the language change they just asked for.
 */
function LanguageSwitcherInner({ current }: { current: Locale }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function switchTo(next: Locale) {
    if (next === current) return;

    const segments = pathname.split("/");
    segments[1] = next;
    // usePathname() drops the query string, so it has to be re-attached:
    // without this, switching language on a page addressed by ?id=... (the
    // result page) silently loses the record being viewed.
    const query = searchParams.toString();
    const target = (segments.join("/") || `/${next}`) + (query ? `?${query}` : "");

    if (tokenStore.access) {
      api.updateProfile({ preferred_language: next } as never).catch(() => {
        /* preference not saved; the UI language still changes */
      });
    }

    startTransition(() => router.push(target));
  }

  return (
    <div className="flex items-center gap-1 rounded-full bg-white p-1 shadow-sm ring-1 ring-leaf-100">
      <Globe className="ml-2 h-4 w-4 text-leaf-700" aria-hidden />
      <div role="group" aria-label="Language" className="flex gap-0.5">
        {locales.map((locale) => (
          <button
            key={locale}
            type="button"
            onClick={() => switchTo(locale)}
            disabled={pending}
            aria-current={locale === current ? "true" : undefined}
            className={cn(
              "min-h-[36px] rounded-full px-3 text-sm font-semibold transition-colors",
              locale === current
                ? "bg-leaf-600 text-white"
                : "text-soil-700 hover:bg-leaf-50",
            )}
          >
            {localeNames[locale]}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * useSearchParams() opts a component into client-side rendering, which Next
 * requires to sit behind a Suspense boundary during static prerender. The
 * boundary lives here rather than at each call site so the header cannot be
 * used in a way that breaks the build.
 *
 * The fallback renders the same-sized pill row, so the header does not shift
 * when the switcher hydrates.
 */
export function LanguageSwitcher({ current }: { current: Locale }) {
  return (
    <Suspense
      fallback={
        <div
          aria-hidden
          className="h-[44px] w-[196px] rounded-full bg-white shadow-sm ring-1 ring-leaf-100"
        />
      }
    >
      <LanguageSwitcherInner current={current} />
    </Suspense>
  );
}

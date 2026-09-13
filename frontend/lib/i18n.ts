import "server-only";

import type { Locale } from "./i18n.client";
import en from "@/locales/en.json";

/**
 * i18n is built on route segments (/mr/dashboard), not a client-side toggle:
 * the correct language is rendered on the server on first paint, the URL is
 * shareable, and there is no flash of English.
 *
 * The English dictionary is the source of truth for the key shape. `mr.json`
 * and `hi.json` are typed as `Dictionary`, so a missing or misspelled key is
 * a build error rather than a blank space on a farmer's screen.
 */

// Re-exported from the client-safe module so there is one definition of the
// locale list, usable from both server and client components.
export { locales, defaultLocale, localeNames, isLocale } from "./i18n.client";
export type { Locale } from "./i18n.client";

export type Dictionary = typeof en;

const dictionaries: Record<Locale, () => Promise<Dictionary>> = {
  en: () => import("@/locales/en.json").then((m) => m.default),
  hi: () => import("@/locales/hi.json").then((m) => m.default as Dictionary),
  mr: () => import("@/locales/mr.json").then((m) => m.default as Dictionary),
};

export async function getDictionary(locale: Locale): Promise<Dictionary> {
  return dictionaries[locale]();
}

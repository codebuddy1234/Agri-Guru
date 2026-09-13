/**
 * The locale constants that client components need.
 *
 * lib/i18n.ts is server-only (it imports the dictionaries, which should never
 * be shipped to the browser in full). This module carries just the small,
 * safe parts so a client component can import them without dragging three
 * translation files into the bundle.
 */

export const locales = ["mr", "hi", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "mr";

export const localeNames: Record<Locale, string> = {
  mr: "मराठी",
  hi: "हिंदी",
  en: "English",
};

export function isLocale(value: string): value is Locale {
  return (locales as readonly string[]).includes(value);
}

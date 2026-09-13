import type { Dictionary, Locale } from "./i18n";

/**
 * Replaces {placeholders} in a translated string.
 *
 * Kept deliberately small: the alternative is pulling in a full ICU message
 * formatter for a handful of simple substitutions.
 */
export function interpolate(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

/** Crop names come from the model in English; the UI shows them translated. */
export function cropName(dict: Dictionary, key: string): string {
  const crops = dict.crops as Record<string, string>;
  // Fall back to the raw key rather than showing nothing if the model ever
  // returns a class the dictionary has not been updated for.
  return crops[key] ?? key;
}

/**
 * The `-u-nu-latn` extension forces Latin digits (95) instead of the
 * Devanagari digits (९५) that mr-IN and hi-IN select by default.
 *
 * This is deliberate, not laziness about localisation. Marathi and Hindi
 * speakers read Latin numerals in everyday digital use, and every number a
 * farmer cross-checks here - the values on a soil health card, a thermometer,
 * a rain gauge - is printed in Latin digits. Rendering the confidence as ९५%
 * beside an input they typed as 95 makes the two look unrelated.
 * Month and day names still localise normally.
 */
const localeTags: Record<Locale, string> = {
  mr: "mr-IN-u-nu-latn",
  hi: "hi-IN-u-nu-latn",
  en: "en-IN-u-nu-latn",
};

export function formatDate(iso: string, locale: Locale): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(localeTags[locale], {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(iso: string, locale: Locale): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(localeTags[locale], {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function formatPercent(value: number, locale: Locale): string {
  return new Intl.NumberFormat(localeTags[locale], {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}

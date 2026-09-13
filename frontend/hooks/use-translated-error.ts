"use client";

import { ApiClientError } from "@/lib/api-client";

type ErrorDict = Record<string, string>;

/**
 * Maps a backend error code to a message in the farmer's language.
 *
 * The backend's own message is English-only, so showing it directly would
 * break localisation at exactly the moment the farmer most needs to
 * understand what happened. The code is the contract; the wording is ours.
 */
export function translateError(err: unknown, errors: ErrorDict, fallback: string): string {
  if (err instanceof ApiClientError) {
    return errors[err.code] ?? fallback;
  }
  return fallback;
}

import { redirect } from "next/navigation";
import { defaultLocale } from "@/lib/i18n";

/** The app is always served under a locale segment, so the bare root sends
 *  the visitor to the default language (Marathi). */
export default function RootPage() {
  redirect(`/${defaultLocale}`);
}

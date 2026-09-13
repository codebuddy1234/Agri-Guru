import type { Metadata, Viewport } from "next";
import { Noto_Sans } from "next/font/google";
import "./globals.css";

/** Noto Sans carries Devanagari, so Marathi and Hindi render in the same
 *  family as English instead of dropping to a mismatched system fallback. */
const noto = Noto_Sans({
  subsets: ["latin", "devanagari"],
  weight: ["400", "600", "700"],
  variable: "--font-noto",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AgriGuru AI",
  description: "Smart agriculture decision support for farmers",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#247937",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html className={noto.variable}>
      <body>{children}</body>
    </html>
  );
}

import Link from "next/link";
import {
  BarChart3,
  CloudSun,
  FlaskConical,
  Landmark,
  Leaf,
  Lock,
  Sprout,
  TrendingUp,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { PlatformModule } from "@/types/api";

const icons: Record<string, LucideIcon> = {
  sprout: Sprout,
  leaf: Leaf,
  "cloud-sun": CloudSun,
  "trending-up": TrendingUp,
  "flask-conical": FlaskConical,
  "bar-chart-3": BarChart3,
  landmark: Landmark,
  "user-check": UserCheck,
};

/**
 * A "coming soon" module renders as a non-interactive div, never a disabled
 * link: there is no route behind it, and a card that looks tappable but does
 * nothing is worse than one that plainly says it is not ready.
 */
export function ModuleCard({
  module,
  locale,
  title,
  description,
  availableLabel,
  comingSoonLabel,
}: {
  module: PlatformModule;
  locale: string;
  title: string;
  description: string;
  availableLabel: string;
  comingSoonLabel: string;
}) {
  const Icon = icons[module.icon] ?? Sprout;
  const available = module.status === "available" && module.route;

  const inner = (
    <>
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
            available ? "bg-leaf-100 text-leaf-700" : "bg-soil-100 text-soil-700/60",
          )}
        >
          <Icon className="h-6 w-6" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          <h3
            className={cn(
              "font-bold",
              available ? "text-soil-900" : "text-soil-700/70",
            )}
          >
            {title}
          </h3>
          <p
            className={cn(
              "mt-0.5 text-sm leading-snug",
              available ? "text-soil-700" : "text-soil-700/60",
            )}
          >
            {description}
          </p>
        </div>
        {!available && (
          <Lock className="h-4 w-4 shrink-0 text-soil-700/40" aria-hidden />
        )}
      </div>
      <span
        className={cn(
          "mt-3 inline-block rounded-full px-3 py-1 text-xs font-bold",
          available
            ? "bg-leaf-600 text-white"
            : "bg-soil-100 text-soil-700/70",
        )}
      >
        {available ? availableLabel : comingSoonLabel}
      </span>
    </>
  );

  const base = "block rounded-2xl border p-5 transition-all";

  if (!available) {
    return (
      <div
        aria-disabled="true"
        className={cn(base, "cursor-not-allowed border-dashed border-soil-100 bg-white/60")}
      >
        {inner}
      </div>
    );
  }

  return (
    <Link
      href={`/${locale}${module.route}`}
      className={cn(
        base,
        "border-leaf-100 bg-white shadow-sm hover:-translate-y-0.5 hover:border-leaf-300 hover:shadow-md",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-leaf-500 focus-visible:ring-offset-2",
      )}
    >
      {inner}
    </Link>
  );
}

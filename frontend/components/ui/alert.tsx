import * as React from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type Tone = "info" | "warning" | "error" | "success";

const tones: Record<Tone, { wrap: string; icon: React.ElementType }> = {
  info: { wrap: "border-leaf-200 bg-leaf-50 text-leaf-900", icon: Info },
  warning: {
    wrap: "border-harvest-400 bg-harvest-50 text-harvest-700",
    icon: AlertTriangle,
  },
  error: { wrap: "border-red-300 bg-red-50 text-red-900", icon: XCircle },
  success: { wrap: "border-leaf-300 bg-leaf-50 text-leaf-800", icon: CheckCircle2 },
};

export function Alert({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const { wrap, icon: Icon } = tones[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-xl border-2 p-4", wrap, className)}
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div className="min-w-0 text-sm leading-relaxed">
        {title && <p className="font-bold">{title}</p>}
        {children}
      </div>
    </div>
  );
}

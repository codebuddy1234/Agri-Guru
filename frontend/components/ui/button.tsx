"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Follows shadcn/ui conventions (vendored component, cn() merging, variant
 * props) without the Radix dependency, since none of these buttons need a
 * portal or composition slot.
 *
 * min-h-[48px] on the default size is not arbitrary: it is the touch-target
 * floor for a farmer using this outdoors, one-handed, on a phone.
 */

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  primary:
    "bg-leaf-600 text-white hover:bg-leaf-700 active:bg-leaf-800 focus-visible:ring-leaf-500",
  secondary:
    "bg-harvest-400 text-soil-900 hover:bg-harvest-500 focus-visible:ring-harvest-500",
  outline:
    "border-2 border-leaf-600 text-leaf-700 bg-white hover:bg-leaf-50 focus-visible:ring-leaf-500",
  ghost: "text-leaf-700 hover:bg-leaf-50 focus-visible:ring-leaf-500",
  danger: "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500",
};

const sizes: Record<Size, string> = {
  sm: "min-h-[40px] px-4 text-sm",
  md: "min-h-[48px] px-5 text-base",
  lg: "min-h-[56px] px-7 text-lg",
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant = "primary", size = "md", loading, disabled, children, ...props },
    ref,
  ) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold",
        "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading && (
        <span
          aria-hidden
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  ),
);
Button.displayName = "Button";

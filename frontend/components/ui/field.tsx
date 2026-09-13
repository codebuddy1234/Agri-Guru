"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * A labelled numeric input with help text, an accepted range, and an error
 * slot.
 *
 * The label/help/range are not decoration. A farmer reading "N" with no unit
 * and no range has no way to know whether 90 is sensible - and for N, P and K
 * specifically, copying a soil health card value in kg/ha would silently
 * produce a wrong recommendation. The help text is the fix for that.
 */

export interface NumberFieldProps {
  id: string;
  label: string;
  help?: string;
  hint?: string;
  unit?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  min?: number;
  max?: number;
  step?: string;
  required?: boolean;
}

export function NumberField({
  id,
  label,
  help,
  hint,
  unit,
  value,
  onChange,
  error,
  min,
  max,
  step = "any",
  required,
}: NumberFieldProps) {
  const describedBy = [help ? `${id}-help` : null, error ? `${id}-error` : null]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-semibold text-soil-900">
        {label}
        {required && <span className="ml-1 text-red-600">*</span>}
      </label>
      {help && (
        <p id={`${id}-help`} className="text-xs leading-relaxed text-soil-700">
          {help}
        </p>
      )}
      <div className="relative">
        <input
          id={id}
          name={id}
          type="number"
          inputMode="decimal"
          step={step}
          min={min}
          max={max}
          value={value}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "min-h-[52px] w-full rounded-xl border-2 bg-white px-4 text-lg text-soil-900",
            "focus:outline-none focus:ring-2 focus:ring-offset-1",
            unit && "pr-16",
            error
              ? "border-red-400 focus:border-red-500 focus:ring-red-400"
              : "border-leaf-200 focus:border-leaf-500 focus:ring-leaf-400",
          )}
        />
        {unit && (
          <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm font-medium text-soil-700">
            {unit}
          </span>
        )}
      </div>
      {hint && !error && <p className="text-xs text-soil-700/80">{hint}</p>}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

export interface TextFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  id: string;
  label: string;
  help?: string;
  error?: string;
  onChange: (value: string) => void;
}

export function TextField({
  id,
  label,
  help,
  error,
  onChange,
  className,
  required,
  ...props
}: TextFieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-semibold text-soil-900">
        {label}
        {required && <span className="ml-1 text-red-600">*</span>}
      </label>
      {help && <p className="text-xs text-soil-700">{help}</p>}
      <input
        id={id}
        name={id}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "min-h-[52px] w-full rounded-xl border-2 bg-white px-4 text-base text-soil-900",
          "focus:outline-none focus:ring-2 focus:ring-offset-1",
          error
            ? "border-red-400 focus:border-red-500 focus:ring-red-400"
            : "border-leaf-200 focus:border-leaf-500 focus:ring-leaf-400",
          className,
        )}
        {...props}
      />
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

import type { Dictionary } from "./i18n";

/**
 * The seven model inputs, described for a farmer.
 *
 * `min`/`max` mirror the backend's accepted ranges in
 * backend/app/ml/crop_recommendation/schema.py. Client validation exists to
 * give immediate feedback, NOT to be trusted - the backend validates every
 * request independently, and these bounds are only a convenience copy.
 *
 * `unit` is deliberately blank for N, P and K. They are unitless ratio values
 * in the training dataset, and printing "kg/ha" beside them would be the
 * single most likely cause of a wrong real-world recommendation.
 */

export interface CropFieldSpec {
  /** API field name, also used as the input id. */
  name: "nitrogen" | "phosphorus" | "potassium" | "temperature" | "humidity" | "ph" | "rainfall";
  section: "soil" | "weather";
  unit: string;
  min: number;
  max: number;
  step: string;
  labelKey: keyof Dictionary["crop"];
  helpKey: keyof Dictionary["crop"];
}

export const CROP_FIELDS: CropFieldSpec[] = [
  { name: "nitrogen",    section: "soil",    unit: "",    min: 0, max: 200, step: "1",    labelKey: "nitrogen",    helpKey: "nitrogenHelp" },
  { name: "phosphorus",  section: "soil",    unit: "",    min: 0, max: 200, step: "1",    labelKey: "phosphorus",  helpKey: "phosphorusHelp" },
  { name: "potassium",   section: "soil",    unit: "",    min: 0, max: 250, step: "1",    labelKey: "potassium",   helpKey: "potassiumHelp" },
  { name: "ph",          section: "soil",    unit: "pH",  min: 0, max: 14,  step: "0.1",  labelKey: "ph",          helpKey: "phHelp" },
  { name: "temperature", section: "weather", unit: "°C",  min: 0, max: 55,  step: "0.1",  labelKey: "temperature", helpKey: "temperatureHelp" },
  { name: "humidity",    section: "weather", unit: "%",   min: 0, max: 100, step: "0.1",  labelKey: "humidity",    helpKey: "humidityHelp" },
  { name: "rainfall",    section: "weather", unit: "mm",  min: 0, max: 500, step: "0.1",  labelKey: "rainfall",    helpKey: "rainfallHelp" },
];

export type CropFormValues = Record<CropFieldSpec["name"], string>;

export const EMPTY_CROP_FORM: CropFormValues = {
  nitrogen: "",
  phosphorus: "",
  potassium: "",
  temperature: "",
  humidity: "",
  ph: "",
  rainfall: "",
};

/**
 * Client-side pre-check. Returns field -> message for anything obviously
 * wrong, so the farmer is not made to wait for a round trip to learn they
 * left a box empty. The backend still validates everything.
 */
export function validateCropForm(
  values: CropFormValues,
  messages: { required: string; range: (min: number, max: number) => string },
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of CROP_FIELDS) {
    const raw = values[field.name].trim();
    if (raw === "") {
      errors[field.name] = messages.required;
      continue;
    }
    const value = Number(raw);
    if (!Number.isFinite(value)) {
      errors[field.name] = messages.range(field.min, field.max);
      continue;
    }
    if (value < field.min || value > field.max) {
      errors[field.name] = messages.range(field.min, field.max);
    }
  }
  return errors;
}

/** Mirrors the backend response envelope in app/schemas/common.py. */

export interface ApiError {
  code: string;
  message: string;
  details: { field: string | null; message: string }[];
  request_id: string | null;
}

export interface ApiSuccess<T> {
  success: true;
  data: T;
}

export interface ApiFailure {
  success: false;
  error: ApiError;
}

export interface PageMeta {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PaginatedSuccess<T> extends ApiSuccess<T[]> {
  meta: PageMeta;
}

export type Language = "mr" | "hi" | "en";
export type AreaUnit = "acre" | "hectare" | "guntha";

export interface User {
  id: string;
  email: string;
  mobile: string | null;
  role: "farmer" | "expert" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface FarmerProfile {
  id: string;
  full_name: string;
  preferred_language: Language;
  state: string | null;
  district: string | null;
  taluka: string | null;
  village: string | null;
  pincode: string | null;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
  updated_at: string;
}

export interface Farm {
  id: string;
  name: string;
  area_value: number;
  area_unit: AreaUnit;
  soil_type: string | null;
  irrigation_source: string | null;
  village: string | null;
  created_at: string;
}

export interface CropCandidate {
  crop: string;
  probability: number;
}

export interface Prediction {
  id: string;
  recommended_crop: string;
  confidence: number | null;
  alternatives: CropCandidate[];
  model_name: string;
  model_version: string;
  created_at: string;
  inputs: Record<string, number>;
  out_of_training_range: string[];
}

export interface PredictionHistoryItem {
  id: string;
  recommended_crop: string;
  confidence: number | null;
  model_version: string;
  created_at: string;
}

export interface PlatformModule {
  key: string;
  icon: string;
  status: "available" | "coming_soon";
  route: string | null;
  phase: number;
}

export interface PredictionInput {
  nitrogen: number;
  phosphorus: number;
  potassium: number;
  temperature: number;
  humidity: number;
  ph: number;
  rainfall: number;
  farm_id?: string | null;
}

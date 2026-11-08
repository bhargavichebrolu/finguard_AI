/**
 * The frozen model's measured limitations, loaded once per session and shown beside every score.
 *
 * The statements come from GET /api/v1/models/metrics, which builds them from the saved Phase 2
 * results. Nothing here contains a figure.
 */
import { createContext, useContext, type ReactNode } from "react";

import { ApiError } from "../services/api";
import { modelsApi, type ModelMetrics } from "../services/endpoints";
import { useApiResource } from "./useApiResource";

export interface ModelLimits {
  metrics: ModelMetrics | null;
  notes: string[];
  error: ApiError | null;
  loading: boolean;
}

const ModelLimitsContext = createContext<ModelLimits | null>(null);

export function ModelLimitsProvider({ children }: { children: ReactNode }) {
  const resource = useApiResource(() => modelsApi.metrics(), []);
  const value: ModelLimits = {
    metrics: resource.data,
    notes: resource.data?.performance_notes ?? [],
    error: resource.error,
    loading: resource.loading,
  };
  return <ModelLimitsContext.Provider value={value}>{children}</ModelLimitsContext.Provider>;
}

export function useModelLimits(): ModelLimits {
  const value = useContext(ModelLimitsContext);
  if (!value) {
    throw new Error("useModelLimits must be used inside ModelLimitsProvider");
  }
  return value;
}

/**
 * Typed calls to every API route the interface uses, grouped by area.
 *
 * Types come from src/types/api.generated.ts, which is generated from the API's own schema.
 */
import type { components, paths } from "../types/api.generated";
import { api } from "./api";

export type Schemas = components["schemas"];
export type CurrentUser = Schemas["CurrentUserView"];
export type TransactionInput = Schemas["TransactionInput"];
export type Prediction = Schemas["PredictionView"];
export type TransactionSummary = Schemas["TransactionSummary"];
export type TransactionDetail = Schemas["TransactionDetail"];
export type Batch = Schemas["BatchView"];
export type InvestigationSummary = Schemas["InvestigationSummary"];
export type InvestigationDetail = Schemas["InvestigationDetail"];
export type InvestigationUpdate = Schemas["InvestigationUpdate"];
export type Note = Schemas["NoteView"];
export type ModelVersion = Schemas["ModelVersionView"];
export type ModelMetrics = Schemas["ModelMetricsView"];
export type ModelReport = Schemas["ModelReportView"];
export type FeatureImportance = Schemas["FeatureImportanceView"];
export type SummaryReport = Schemas["SummaryReport"];
export type AppSettings = Schemas["SettingsView"];
export type SystemStatus = Schemas["SystemStatus"];
export type User = Schemas["UserView"];
export type UserCreate = Schemas["UserCreate"];
export type UserUpdate = Schemas["UserUpdate"];
export type Assignee = Schemas["AssigneeView"];
export type AuditEntry = Schemas["AuditLogView"];

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export type TransactionQuery = NonNullable<
  paths["/api/v1/transactions"]["get"]["parameters"]["query"]
>;
export type InvestigationQuery = NonNullable<
  paths["/api/v1/investigations"]["get"]["parameters"]["query"]
>;
export type ReportType = "predictions" | "flag_summary" | "investigations" | "model_evaluation";

const V1 = "/api/v1";

export const authApi = {
  async signIn(email: string, password: string): Promise<CurrentUser> {
    return (await api.post<CurrentUser>(`${V1}/auth/session`, { email, password })).data;
  },
  async signOut(): Promise<void> {
    await api.delete(`${V1}/auth/session`);
  },
  async me(): Promise<CurrentUser> {
    return (await api.get<CurrentUser>(`${V1}/auth/me`)).data;
  },
};

export const transactionsApi = {
  async predict(input: TransactionInput): Promise<Prediction> {
    return (await api.post<Prediction>(`${V1}/transactions/predict`, input)).data;
  },
  async list(query: TransactionQuery): Promise<Page<TransactionSummary>> {
    return (await api.get<Page<TransactionSummary>>(`${V1}/transactions`, { params: query })).data;
  },
  async get(id: string): Promise<TransactionDetail> {
    return (await api.get<TransactionDetail>(`${V1}/transactions/${id}`)).data;
  },
};

export const batchesApi = {
  async upload(file: File, onProgress?: (fraction: number) => void): Promise<Batch> {
    const form = new FormData();
    form.append("file", file);
    const response = await api.post<Batch>(`${V1}/batches/upload`, form, {
      onUploadProgress: (event) => {
        if (onProgress && event.total) onProgress(event.loaded / event.total);
      },
    });
    return response.data;
  },
  async list(limit = 20, offset = 0): Promise<Page<Batch>> {
    return (await api.get<Page<Batch>>(`${V1}/batches`, { params: { limit, offset } })).data;
  },
  async get(id: string): Promise<Batch> {
    return (await api.get<Batch>(`${V1}/batches/${id}`)).data;
  },
  async results(id: string, limit: number, offset: number): Promise<Page<TransactionSummary>> {
    const params = { limit, offset, sort_by: "model_score", sort_order: "desc" };
    return (await api.get<Page<TransactionSummary>>(`${V1}/batches/${id}/results`, { params })).data;
  },
};

export const investigationsApi = {
  async list(query: InvestigationQuery): Promise<Page<InvestigationSummary>> {
    return (await api.get<Page<InvestigationSummary>>(`${V1}/investigations`, { params: query })).data;
  },
  async get(id: string): Promise<InvestigationDetail> {
    return (await api.get<InvestigationDetail>(`${V1}/investigations/${id}`)).data;
  },
  async update(id: string, change: InvestigationUpdate): Promise<InvestigationDetail> {
    return (await api.patch<InvestigationDetail>(`${V1}/investigations/${id}`, change)).data;
  },
  async addNote(id: string, note: string): Promise<Note> {
    return (await api.post<Note>(`${V1}/investigations/${id}/notes`, { note })).data;
  },
};

export const modelsApi = {
  async active(): Promise<ModelVersion> {
    return (await api.get<ModelVersion>(`${V1}/models/active`)).data;
  },
  async metrics(): Promise<ModelMetrics> {
    return (await api.get<ModelMetrics>(`${V1}/models/metrics`)).data;
  },
  async report(): Promise<ModelReport> {
    return (await api.get<ModelReport>(`${V1}/models/report`)).data;
  },
  async featureImportance(): Promise<FeatureImportance> {
    return (await api.get<FeatureImportance>(`${V1}/models/feature-importance`)).data;
  },
};

export const reportsApi = {
  async summary(): Promise<SummaryReport> {
    return (await api.get<SummaryReport>(`${V1}/reports/summary`)).data;
  },
};

export const settingsApi = {
  async get(): Promise<AppSettings> {
    return (await api.get<AppSettings>(`${V1}/settings`)).data;
  },
  async update(highRiskBoundary: number): Promise<AppSettings> {
    const body = { high_risk_boundary: highRiskBoundary };
    return (await api.patch<AppSettings>(`${V1}/settings`, body)).data;
  },
};

export const systemApi = {
  async status(): Promise<SystemStatus> {
    return (await api.get<SystemStatus>(`${V1}/system/status`)).data;
  },
  async health(): Promise<{ status: string }> {
    return (await api.get<{ status: string }>("/health")).data;
  },
};

export const usersApi = {
  async list(limit = 50, offset = 0): Promise<Page<User>> {
    return (await api.get<Page<User>>(`${V1}/users`, { params: { limit, offset } })).data;
  },
  async create(user: UserCreate): Promise<User> {
    return (await api.post<User>(`${V1}/users`, user)).data;
  },
  async update(id: string, change: UserUpdate): Promise<User> {
    return (await api.patch<User>(`${V1}/users/${id}`, change)).data;
  },
  async assignable(): Promise<Assignee[]> {
    return (await api.get<Assignee[]>(`${V1}/users/assignable`)).data;
  },
};

export const auditApi = {
  async list(limit = 20, offset = 0): Promise<Page<AuditEntry>> {
    return (await api.get<Page<AuditEntry>>(`${V1}/audit-logs`, { params: { limit, offset } })).data;
  },
};

/** The CSV downloads the interface offers, as paths under /api/v1. */
export const downloadPaths = {
  batchResults: (id: string) => `${V1}/batches/${id}/export`,
  batchErrors: (id: string) => `${V1}/batches/${id}/errors`,
  report: (type: ReportType) => `${V1}/reports/export?report_type=${type}`,
};

/** Fetch a file through the signed-in client and hand it to the browser as a download. */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const response = await api.get<Blob>(path, { responseType: "blob" });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const match = /filename="([^"]+)"/.exec(disposition);
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = match?.[1] ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

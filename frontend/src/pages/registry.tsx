/**
 * Every page, its address, its navigation entry and the permission it needs, in PRD 7.4 order.
 * Routes and navigation are both built from this list, so they cannot disagree.
 *
 * Each page is loaded on first visit with React.lazy, so the chart library and the larger pages
 * are not part of the first download.
 */
import {
  BarChart3,
  Calculator,
  ClipboardList,
  FileDown,
  FileSpreadsheet,
  LayoutDashboard,
  Lightbulb,
  Search,
  Server,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { lazy, type ComponentType, type ReactElement } from "react";

/** Load one named export of a page module as a lazy component. */
function page<Name extends string>(load: () => Promise<Record<Name, ComponentType>>, name: Name) {
  return lazy(async () => ({ default: (await load())[name] }));
}

const DashboardPage = page(() => import("./DashboardPage"), "DashboardPage");
const TransactionAnalysisPage = page(() => import("./TransactionAnalysisPage"), "TransactionAnalysisPage");
const BatchAnalysisPage = page(() => import("./BatchAnalysisPage"), "BatchAnalysisPage");
const TransactionExplorerPage = page(() => import("./TransactionExplorerPage"), "TransactionExplorerPage");
const InvestigationCentrePage = page(() => import("./InvestigationCentrePage"), "InvestigationCentrePage");
const ModelPerformancePage = page(() => import("./ModelPerformancePage"), "ModelPerformancePage");
const ExplainabilityPage = page(() => import("./ExplainabilityPage"), "ExplainabilityPage");
const ReportsPage = page(() => import("./ReportsPage"), "ReportsPage");
const SettingsPage = page(() => import("./SettingsPage"), "SettingsPage");
const SystemInformationPage = page(() => import("./SystemInformationPage"), "SystemInformationPage");

export interface PageDefinition {
  path: string;
  label: string;
  icon: LucideIcon;
  permission: string;
  element: ReactElement;
}

export const PAGES: PageDefinition[] = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard, permission: "view_summary", element: <DashboardPage /> },
  { path: "/analyse", label: "Transaction Analysis", icon: Calculator, permission: "predict", element: <TransactionAnalysisPage /> },
  { path: "/batches", label: "CSV Batch Analysis", icon: FileSpreadsheet, permission: "upload_batch", element: <BatchAnalysisPage /> },
  { path: "/transactions", label: "Transaction Explorer", icon: Search, permission: "view_transactions", element: <TransactionExplorerPage /> },
  { path: "/investigations", label: "Investigation Centre", icon: ClipboardList, permission: "view_investigations", element: <InvestigationCentrePage /> },
  { path: "/models", label: "Model Performance", icon: BarChart3, permission: "view_models", element: <ModelPerformancePage /> },
  { path: "/explainability", label: "Explainable AI", icon: Lightbulb, permission: "view_models", element: <ExplainabilityPage /> },
  { path: "/reports", label: "Reports", icon: FileDown, permission: "export_reports", element: <ReportsPage /> },
  { path: "/settings", label: "Settings", icon: Settings, permission: "view_settings", element: <SettingsPage /> },
  { path: "/system", label: "System Information", icon: Server, permission: "view_system_status", element: <SystemInformationPage /> },
];

/** The pages a role may open, in navigation order. */
export function visiblePages(can: (permission: string) => boolean): PageDefinition[] {
  return PAGES.filter((entry) => can(entry.permission));
}

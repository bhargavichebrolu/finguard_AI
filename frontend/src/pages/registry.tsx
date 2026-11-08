/**
 * Every page, its address, its navigation entry and the permission it needs, in PRD 7.4 order.
 * Routes and navigation are both built from this list, so they cannot disagree.
 */
import { Calculator, FileSpreadsheet, LayoutDashboard, Lightbulb, Search, Server, type LucideIcon } from "lucide-react";
import type { ReactElement } from "react";

import { BatchAnalysisPage } from "./BatchAnalysisPage";
import { DashboardPage } from "./DashboardPage";
import { ExplainabilityPage } from "./ExplainabilityPage";
import { SystemInformationPage } from "./SystemInformationPage";
import { TransactionAnalysisPage } from "./TransactionAnalysisPage";
import { TransactionExplorerPage } from "./TransactionExplorerPage";

export interface PageDefinition {
  path: string;
  label: string;
  icon: LucideIcon;
  permission: string;
  element: ReactElement;
}

export const PAGES: PageDefinition[] = [
  {
    path: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    permission: "view_summary",
    element: <DashboardPage />,
  },
  {
    path: "/analyse",
    label: "Transaction Analysis",
    icon: Calculator,
    permission: "predict",
    element: <TransactionAnalysisPage />,
  },
  {
    path: "/batches",
    label: "CSV Batch Analysis",
    icon: FileSpreadsheet,
    permission: "upload_batch",
    element: <BatchAnalysisPage />,
  },
  {
    path: "/transactions",
    label: "Transaction Explorer",
    icon: Search,
    permission: "view_transactions",
    element: <TransactionExplorerPage />,
  },
  {
    path: "/explainability",
    label: "Explainable AI",
    icon: Lightbulb,
    permission: "view_models",
    element: <ExplainabilityPage />,
  },
  {
    path: "/system",
    label: "System Information",
    icon: Server,
    permission: "view_system_status",
    element: <SystemInformationPage />,
  },
];

/** The pages a role may open, in navigation order. */
export function visiblePages(can: (permission: string) => boolean): PageDefinition[] {
  return PAGES.filter((page) => can(page.permission));
}

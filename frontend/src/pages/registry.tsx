/**
 * Every page, its address, its navigation entry and the permission it needs, in PRD 7.4 order.
 * Routes and navigation are both built from this list, so they cannot disagree.
 */
import { Server, type LucideIcon } from "lucide-react";
import type { ReactElement } from "react";

import { SystemInformationPage } from "./SystemInformationPage";

export interface PageDefinition {
  path: string;
  label: string;
  icon: LucideIcon;
  permission: string;
  element: ReactElement;
}

export const PAGES: PageDefinition[] = [
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

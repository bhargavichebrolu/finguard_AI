/**
 * The signed-in frame: a collapsible left navigation, a top bar and the content area (PRD 7.3).
 * Navigation lists only pages the signed-in role may use, as reported by the API.
 */
import { LogOut, Menu, PanelLeftClose, PanelLeftOpen, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { DemoBadge } from "../components/badges";
import { useAuth } from "../hooks/useAuth";
import { visiblePages } from "../pages/registry";
import { humanise } from "../utils/format";

export function AppLayout() {
  const { user, can, signOut } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pages = visiblePages(can);
  const isDemo = user?.role === "demo";
  const menuButton = useRef<HTMLButtonElement>(null);

  // On narrow screens the menu covers the page, so Escape closes it and returns focus to the
  // button that opened it.
  useEffect(() => {
    if (!mobileOpen) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setMobileOpen(false);
      menuButton.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  return (
    <div className={`shell ${collapsed ? "shell-collapsed" : ""}`}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="topbar">
        <button
          ref={menuButton}
          type="button"
          className="button icon ghost mobile-only"
          aria-label="Open navigation"
          aria-expanded={mobileOpen}
          aria-controls="main-navigation"
          onClick={() => setMobileOpen((open) => !open)}
        >
          <Menu aria-hidden="true" />
        </button>
        <div className="brand">
          <ShieldCheck aria-hidden="true" />
          <span>FinGuard AI</span>
        </div>
        <p className="topbar-note">Research and demonstration only. Synthetic PaySim data.</p>
        <div className="topbar-user">
          <span className="user-email">{user?.email}</span>
          <span className="badge badge-status">{humanise(user?.role ?? "")}</span>
          <button type="button" className="button secondary sign-out" onClick={() => void signOut()}>
            <LogOut aria-hidden="true" />
            <span className="sign-out-label">Sign out</span>
          </button>
        </div>
      </header>

      {isDemo ? (
        <div className="demo-banner" role="note">
          <DemoBadge /> Demo mode: everything you create here is a synthetic sample record, kept apart
          from other users' records.
        </div>
      ) : null}

      <nav
        id="main-navigation"
        className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}
        aria-label="Main navigation"
      >
        <button
          type="button"
          className="button icon ghost desktop-only collapse-toggle"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((value) => !value)}
        >
          {collapsed ? <PanelLeftOpen aria-hidden="true" /> : <PanelLeftClose aria-hidden="true" />}
        </button>
        <ul>
          {pages.map((page) => (
            <li key={page.path}>
              <NavLink
                to={page.path}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                onClick={() => setMobileOpen(false)}
                title={collapsed ? page.label : undefined}
              >
                <page.icon aria-hidden="true" />
                <span className="nav-label">{page.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <main id="main-content" className="content" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}

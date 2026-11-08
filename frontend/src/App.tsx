import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ForbiddenPage, NotFoundPage, RequireAuth, RequirePermission } from "./components/guards";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { ModelLimitsProvider } from "./hooks/useModelLimits";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { PAGES, visiblePages } from "./pages/registry";

/** Send the root address to the first page this role may open. */
function HomeRedirect() {
  const { can } = useAuth();
  const first = visiblePages(can)[0];
  return first ? <Navigate to={first.path} replace /> : <ForbiddenPage />;
}

/** All routes. Signed-in pages share the layout and the model's limitations. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <ModelLimitsProvider>
              <AppLayout />
            </ModelLimitsProvider>
          </RequireAuth>
        }
      >
        <Route index element={<HomeRedirect />} />
        {PAGES.map((page) => (
          <Route
            key={page.path}
            path={page.path.slice(1)}
            element={<RequirePermission permission={page.permission}>{page.element}</RequirePermission>}
          />
        ))}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

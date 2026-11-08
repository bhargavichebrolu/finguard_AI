/**
 * Render the real application routes at a chosen address, with the real providers.
 */
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../../src/App";
import { AuthProvider } from "../../src/hooks/useAuth";

export function renderApp(path = "/") {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </AuthProvider>,
  );
}

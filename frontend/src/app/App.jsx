import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ForgotPasswordPage, LoginPage, ResetPasswordPage, SignupPage } from "../features/auth/pages";
import { PortalHomePage } from "../features/portal/pages";
import { OverviewPage } from "../features/reports/pages";
import { AuthLayout } from "../layouts/AuthLayout";
import { PortalLayout } from "../layouts/PortalLayout";
import { StaffLayout } from "../layouts/StaffLayout";
import { RedirectIfLoggedIn, RequireRole } from "./guards";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Retrying a 403 or 404 only delays the error message.
      retry: (count, error) => error.status >= 500 && count < 2,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route element={<RedirectIfLoggedIn />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
            </Route>
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password/:uid/:token" element={<ResetPasswordPage />} />
          </Route>

          <Route element={<RequireRole roles={["admin", "staff"]} />}>
            <Route element={<StaffLayout />}>
              <Route path="/" element={<OverviewPage />} />
            </Route>
          </Route>

          <Route element={<RequireRole roles={["customer"]} />}>
            <Route element={<PortalLayout />}>
              <Route path="/portal" element={<PortalHomePage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

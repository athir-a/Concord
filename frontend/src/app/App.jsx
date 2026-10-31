import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ForgotPasswordPage, LoginPage, ResetPasswordPage, SignupPage } from "../features/auth/pages";
import { BillingPage } from "../features/billing/pages";
import { CatalogPage } from "../features/catalog/pages";
import { CustomerDetailPage, CustomersPage } from "../features/customers/pages";
import { InvoiceDetailPage, InvoicePrintPage, InvoicesPage } from "../features/invoices/pages";
import { PaymentsPage } from "../features/payments/pages";
import { PortalHomePage, PortalInvoicePage, PortalSubscriptionPage } from "../features/portal/pages";
import { OverviewPage, ReportsPage } from "../features/reports/pages";
import { NewSubscriptionPage, SubscriptionDetailPage, SubscriptionsPage } from "../features/subscriptions/pages";
import { TeamPage } from "../features/team/pages";
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

          <Route element={<RequireRole roles={["admin", "staff", "customer"]} />}>
            <Route path="/invoices/:id/print" element={<InvoicePrintPage />} />
          </Route>

          <Route element={<RequireRole roles={["admin", "staff"]} />}>
            <Route element={<StaffLayout />}>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/customers" element={<CustomersPage />} />
              <Route path="/customers/:id" element={<CustomerDetailPage />} />
              <Route path="/subscriptions" element={<SubscriptionsPage />} />
              <Route path="/subscriptions/new" element={<NewSubscriptionPage />} />
              <Route path="/subscriptions/:id" element={<SubscriptionDetailPage />} />
              <Route path="/invoices" element={<InvoicesPage />} />
              <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
              <Route path="/payments" element={<PaymentsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/catalog" element={<CatalogPage />} />
              <Route element={<RequireRole roles={["admin"]} />}>
                <Route path="/billing" element={<BillingPage />} />
                <Route path="/team" element={<TeamPage />} />
              </Route>
            </Route>
          </Route>

          <Route element={<RequireRole roles={["customer"]} />}>
            <Route element={<PortalLayout />}>
              <Route path="/portal" element={<PortalHomePage />} />
              <Route path="/portal/subscriptions/:id" element={<PortalSubscriptionPage />} />
              <Route path="/portal/invoices/:id" element={<PortalInvoicePage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

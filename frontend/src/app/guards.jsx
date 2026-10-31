import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Button } from "../components/Button";
import { homeFor, useAuth } from "./auth";

function FullPageMessage({ children }) {
  return <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-ink-muted">{children}</div>;
}

export function RequireRole({ roles }) {
  const { user, isLoading, error, refetch } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullPageMessage>Loading…</FullPageMessage>;
  if (error) {
    return (
      <FullPageMessage>
        <p>{error.message}</p>
        <Button variant="secondary" onClick={() => refetch()}>Try again</Button>
      </FullPageMessage>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!roles.includes(user.role)) return <Navigate to={homeFor(user)} replace />;
  return <Outlet />;
}

/** Login and signup pages: someone already logged in goes to their home. */
export function RedirectIfLoggedIn() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <FullPageMessage>Loading…</FullPageMessage>;
  if (user) return <Navigate to={homeFor(user)} replace />;
  return <Outlet />;
}

import { useAuth } from "../../app/auth";

export function OverviewPage() {
  const { user } = useAuth();
  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Overview</h1>
      <p className="mt-1 text-ink-muted">Logged in as {user.email}. Business metrics arrive with the reports milestone.</p>
    </>
  );
}

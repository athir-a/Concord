import { useAuth } from "../../app/auth";

export function PortalHomePage() {
  const { user } = useAuth();
  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Your subscriptions</h1>
      <p className="mt-1 text-ink-muted">Welcome, {user.name || user.email}. You don't have any subscriptions yet.</p>
    </>
  );
}

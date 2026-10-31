import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../app/auth";
import { Button } from "../components/Button";
import { Logo } from "../components/Logo";

export function PortalLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-4xl items-center justify-between gap-4 px-4">
          <Logo />
          <div className="flex min-w-0 items-center gap-3">
            <span className="truncate text-ink-muted">{user.email}</span>
            <Button
              variant="ghost"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-4xl p-4 md:py-8">
        <Outlet />
      </main>
    </div>
  );
}

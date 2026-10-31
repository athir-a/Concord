import { LayoutDashboard, LogOut } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../app/auth";
import { Logo } from "../components/Logo";

const NAV = [
  { group: "Revenue", items: [{ to: "/", label: "Overview", icon: LayoutDashboard, end: true }] },
];

function navClass({ isActive }) {
  return `flex h-8 items-center gap-2.5 rounded-md px-2.5 transition-colors duration-150 ${
    isActive ? "bg-accent-soft font-medium text-accent" : "text-ink-muted hover:bg-canvas hover:text-ink"
  }`;
}

export function StaffLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col border-b border-line bg-surface p-3 md:sticky md:top-0 md:h-screen md:w-56 md:border-r md:border-b-0">
        <Logo className="px-2.5 py-2" />
        <nav aria-label="Main" className="mt-4 flex-1 space-y-5">
          {NAV.map(({ group, items }) => (
            <div key={group}>
              <p className="mb-1 px-2.5 text-xs font-medium text-ink-faint">{group}</p>
              {items.map(({ to, label, icon: Icon, end }) => (
                <NavLink key={to} to={to} end={end} className={navClass}>
                  <Icon size={16} aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="mt-4 flex items-center justify-between gap-2 border-t border-line px-2.5 pt-3">
          <div className="min-w-0">
            <p className="truncate font-medium">{user.name || user.email}</p>
            <p className="text-xs text-ink-muted capitalize">{user.role}</p>
          </div>
          <button
            type="button"
            aria-label="Log out"
            title="Log out"
            className="rounded-md p-1.5 text-ink-muted hover:bg-canvas hover:text-ink"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-4 md:p-8">
        <Outlet />
      </main>
    </div>
  );
}

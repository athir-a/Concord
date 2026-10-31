import { BarChart3, Boxes, CreditCard, FileText, LayoutDashboard, LogOut, PlayCircle, Repeat, Users, UsersRound } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../app/auth";
import { Logo } from "../components/Logo";

const NAV = [
  {
    group: "Revenue",
    items: [
      { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
      { to: "/subscriptions", label: "Subscriptions", icon: Repeat },
      { to: "/invoices", label: "Invoices", icon: FileText },
      { to: "/payments", label: "Payments", icon: CreditCard },
      { to: "/billing", label: "Billing", icon: PlayCircle, admin: true },
      { to: "/reports", label: "Reports", icon: BarChart3 },
    ],
  },
  { group: "Customers", items: [{ to: "/customers", label: "Customers", icon: Users }] },
  {
    group: "Setup",
    items: [
      { to: "/catalog", label: "Catalog", icon: Boxes },
      { to: "/team", label: "Team", icon: UsersRound, admin: true },
    ],
  },
];

function navClass({ isActive }) {
  return `flex h-8 shrink-0 items-center gap-2.5 rounded-md px-2.5 whitespace-nowrap transition-colors duration-150 ${
    isActive ? "bg-accent-soft font-medium text-accent" : "text-ink-muted hover:bg-canvas hover:text-ink"
  }`;
}

export function StaffLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user.role === "admin";

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col border-b border-line bg-surface p-3 md:sticky md:top-0 md:h-screen md:w-56 md:border-r md:border-b-0">
        <div className="flex items-center justify-between md:block">
          <Logo className="px-2.5 py-1 md:py-2" />
          <button
            type="button"
            aria-label="Log out"
            className="rounded-md p-1.5 text-ink-muted hover:bg-canvas hover:text-ink md:hidden"
            onClick={async () => { await logout(); navigate("/login"); }}
          >
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
        {/* On a phone the groups become one row you can swipe. */}
        <nav aria-label="Main" className="mt-2 flex flex-1 gap-1 overflow-x-auto md:mt-4 md:block md:space-y-5 md:overflow-y-auto">
          {NAV.map(({ group, items }) => (
            <div key={group} className="contents md:block">
              <p className="mb-1 hidden px-2.5 text-xs font-medium text-ink-faint md:block">{group}</p>
              {items.filter((item) => !item.admin || isAdmin).map(({ to, label, icon: Icon, end }) => (
                <NavLink key={to} to={to} end={end} className={navClass}>
                  <Icon size={16} aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="mt-4 hidden items-center justify-between gap-2 border-t border-line px-2.5 pt-3 md:flex">
          <div className="min-w-0">
            <p className="truncate font-medium">{user.name || user.email}</p>
            <p className="text-xs text-ink-muted capitalize">{user.role}</p>
          </div>
          <button
            type="button"
            aria-label="Log out"
            title="Log out"
            className="rounded-md p-1.5 text-ink-muted hover:bg-canvas hover:text-ink"
            onClick={async () => { await logout(); navigate("/login"); }}
          >
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-4 md:p-8">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

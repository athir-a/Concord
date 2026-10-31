import { Outlet } from "react-router-dom";
import { Logo } from "../components/Logo";

export function AuthLayout() {
  return (
    <main className="flex min-h-screen flex-col items-center px-4 pt-[14vh] pb-10">
      <Logo className="mb-8 text-lg" />
      <div className="w-full max-w-sm rounded-lg border border-line bg-surface p-6">
        <Outlet />
      </div>
      <p className="mt-6 text-ink-faint">One platform. Every operation in sync.</p>
    </main>
  );
}

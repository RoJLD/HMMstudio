import { Link, Outlet, useLocation } from "react-router-dom";
import { ThemeToggle } from "./ThemeToggle";

const NAV_MAIN = [
  { to: "/", label: "Home" },
  { to: "/data", label: "Data" },
  { to: "/fit", label: "Fit" },
  { to: "/topology", label: "Topology editor" },
] as const;

const NAV_LEARN = [
  { to: "/academy", label: "Academy" },
] as const;

const NAV_SYSTEM = [
  { to: "/settings", label: "Settings" },
] as const;

export default function Layout() {
  const location = useLocation();

  function navLink(to: string, label: string) {
    // Academy is active for /academy and /academy/:id
    const active =
      to === "/"
        ? location.pathname === "/"
        : location.pathname === to || location.pathname.startsWith(to + "/");
    return (
      <Link
        key={to}
        to={to}
        className={
          "px-3 py-2 rounded text-sm " +
          (active
            ? "bg-brand-600 text-white"
            : "text-slate-300 hover:bg-slate-800 hover:text-white")
        }
      >
        {label}
      </Link>
    );
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-slate-900 text-slate-100 p-4 flex flex-col gap-2">
        <h1 className="text-lg font-semibold mb-4">hmm-studio</h1>
        <nav className="flex flex-col gap-1">
          {NAV_MAIN.map((item) => navLink(item.to, item.label))}
          <hr className="border-slate-700 my-2" />
          {NAV_LEARN.map((item) => navLink(item.to, item.label))}
          <hr className="border-slate-700 my-2" />
          {NAV_SYSTEM.map((item) => navLink(item.to, item.label))}
        </nav>
        <div className="mt-auto">
          <div className="mb-2"><ThemeToggle /></div>
          <div className="text-xs text-slate-500">v0.1 · skeleton</div>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto dark:bg-slate-900 dark:text-slate-200">
        <Outlet />
      </main>
    </div>
  );
}

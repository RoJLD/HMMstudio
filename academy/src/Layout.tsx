import { Link, Outlet, useLocation } from "react-router-dom";
import { ThemeToggle } from "./components/ThemeToggle";
import { getTitle } from "./runtimeConfig";

export default function Layout() {
  const location = useLocation();
  const onIndex =
    location.pathname === "/academy" || location.pathname === "/";

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-slate-900 text-slate-100 p-4 flex flex-col gap-2">
        <Link to="/academy" className="text-lg font-semibold mb-4">
          {getTitle()}
        </Link>
        <nav className="flex flex-col gap-1">
          <Link
            to="/academy"
            className={
              "px-3 py-2 rounded text-sm " +
              (onIndex
                ? "bg-brand-600 text-white"
                : "text-slate-300 hover:bg-slate-800 hover:text-white")
            }
          >
            All lessons
          </Link>
        </nav>
        <div className="mt-auto">
          <div className="mb-2">
            <ThemeToggle />
          </div>
          <div className="text-xs text-slate-500">v{__APP_VERSION__}</div>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto dark:bg-slate-900 dark:text-slate-200">
        <Outlet />
      </main>
    </div>
  );
}

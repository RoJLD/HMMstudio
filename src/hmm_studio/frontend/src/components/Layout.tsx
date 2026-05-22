import { Link, Outlet, useLocation } from "react-router-dom";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/data", label: "Data" },
  { to: "/fit", label: "Fit" },
  { to: "/topology", label: "Topology editor" },
] as const;

export default function Layout() {
  const location = useLocation();
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-slate-900 text-slate-100 p-4 flex flex-col gap-2">
        <h1 className="text-lg font-semibold mb-4">hmm-studio</h1>
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={
                  "px-3 py-2 rounded text-sm " +
                  (active
                    ? "bg-brand-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white")
                }
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto text-xs text-slate-500">v0.1 · skeleton</div>
      </aside>
      <main className="flex-1 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}

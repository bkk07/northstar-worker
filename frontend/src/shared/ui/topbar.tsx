import { Menu } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

function humanize(seg: string) {
  return seg.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function useCrumbs() {
  const { pathname } = useLocation();
  const segs = pathname.split("/").filter(Boolean);
  // [section, ...rest] e.g. ops/tickets/TCK-101
  const section = segs[0] ? humanize(segs[0]) : "Home";
  const rest = segs.slice(1, 3).map(humanize);
  const sectionHref = segs[0] ? `/${segs[0]}` : "/";
  return { section, rest, sectionHref };
}

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { section, rest, sectionHref } = useCrumbs();
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center gap-2 px-4 py-2.5 sm:px-6 lg:px-8">
        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={onMenu}
          aria-label="Open navigation"
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900 lg:hidden"
        >
          <Menu aria-hidden className="h-5 w-5" />
        </button>

        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="flex min-w-0 items-center gap-1.5 truncate text-[13px] text-slate-500">
            <li className="shrink-0">
              <Link to="/" className="font-medium text-slate-700 hover:text-slate-900">
                Northstar Commerce
              </Link>
            </li>
            <li aria-hidden className="shrink-0 text-slate-300">
              /
            </li>
            <li className="shrink-0">
              <Link to={sectionHref} className="hover:text-slate-900">
                {section}
              </Link>
            </li>
            {rest.map((r) => (
              <span key={r} className="flex min-w-0 items-center gap-1.5">
                <span aria-hidden className="shrink-0 text-slate-300">
                  /
                </span>
                <span className="truncate text-slate-400">{r}</span>
              </span>
            ))}
          </ol>
        </nav>

        {/* Environment pill + health dot */}
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
            <span aria-hidden className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75 motion-reduce:animate-none" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </span>
            Local sandbox
          </span>
        </div>
      </div>
    </header>
  );
}

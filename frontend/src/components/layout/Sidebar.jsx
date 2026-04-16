// src/components/layout/Sidebar.jsx
import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Briefcase, Mic, Brain,
  ChevronLeft, ChevronRight, Sparkles, Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const NAV = [
  { to: "/",           icon: LayoutDashboard, labelKey: "navDashboard",  color: "text-indigo-400"  },
  { to: "/jobs",       icon: Briefcase,       labelKey: "navJobs",        color: "text-violet-400"  },
  { to: "/interviews", icon: Mic,             labelKey: "navInterviews",  color: "text-sky-400"     },
  { to: "/softskills", icon: Brain,           labelKey: "navSoftSkills",  color: "text-emerald-400" },
];

function NavItem({ item, collapsed }) {
  const { t } = useI18n();
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      className={({ isActive }) => cn(
        "relative flex items-center gap-3 rounded-xl text-[13px] font-medium transition-all duration-150 group",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50",
        collapsed
          ? "h-10 w-10 mx-auto justify-center"
          : "px-3 py-2.5",
        isActive
          ? "bg-white/[0.09] text-white"
          : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
      )}
    >
      {({ isActive }) => (
        <>
          {/* Active indicator bar */}
          {isActive && !collapsed && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-[22px] rounded-r-full bg-indigo-400" />
          )}

          <item.icon className={cn(
            "shrink-0 transition-colors",
            collapsed ? "w-[18px] h-[18px]" : "w-4 h-4 ml-1",
            isActive ? "text-white" : item.color
          )} />

          {!collapsed && <span className="truncate leading-none">{t(item.labelKey)}</span>}

          {/* Tooltip when collapsed */}
          {collapsed && (
            <div className="absolute left-full ml-3 px-2.5 py-1.5 text-xs bg-slate-800 border border-slate-700 text-slate-100 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-150 whitespace-nowrap pointer-events-none shadow-xl z-[100]">
              {t(item.labelKey)}
              <span className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-800" />
            </div>
          )}
        </>
      )}
    </NavLink>
  );
}

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { lang, setLanguage, t } = useI18n();

  return (
    <aside
      className={cn(
        "h-screen flex flex-col shrink-0 transition-[width] duration-300 ease-in-out will-change-[width]",
        "bg-slate-950 border-r border-white/[0.06]",
        collapsed ? "w-[64px]" : "w-[228px]"
      )}
    >
      {/* ── Logo ─────────────────────────────────────────────────────────── */}
      <div className={cn(
        "h-16 flex items-center shrink-0 border-b border-white/[0.06]",
        collapsed ? "justify-center px-0" : "px-4 gap-3"
      )}>
        <div className="relative shrink-0">
          <div className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-900/40">
            <Sparkles className="w-[15px] h-[15px] text-white" />
          </div>
          {/* Glow */}
          <div className="absolute inset-0 rounded-[10px] bg-gradient-to-br from-indigo-500 to-violet-600 blur-md opacity-30 -z-10" />
        </div>

        {!collapsed && (
          <div className="min-w-0">
            <p className="text-[13px] font-bold text-white tracking-tight leading-none">
              AI Analyzer
            </p>
            <p className="text-[10px] text-slate-500 mt-0.5 tracking-wide">
              HR Intelligence
            </p>
          </div>
        )}
      </div>

      {/* ── Navigation ───────────────────────────────────────────────────── */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {!collapsed && (
          <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-600 px-3 mb-3">
            {t("sidebarMenu") || "Menu"}
          </p>
        )}
        {NAV.map((item) => (
          <NavItem key={item.to} item={item} collapsed={collapsed} />
        ))}
      </nav>

      {/* ── Language toggle ───────────────────────────────────────────────── */}
      <div className={cn("px-3 pb-3", collapsed && "flex justify-center")}>
        {collapsed ? (
          <button
            onClick={() => setLanguage(lang === "en" ? "fr" : "en")}
            className="w-10 h-8 rounded-lg bg-white/[0.07] hover:bg-white/[0.12] text-slate-400 hover:text-slate-200 text-[10px] font-bold uppercase transition-all flex items-center justify-center border border-white/[0.08]"
          >
            {lang}
          </button>
        ) : (
          <div className="flex items-center bg-white/[0.05] rounded-lg p-0.5 border border-white/[0.07]">
            {["en", "fr"].map((l) => (
              <button
                key={l}
                onClick={() => setLanguage(l)}
                className={cn(
                  "flex-1 h-[26px] rounded-md text-[11px] font-semibold uppercase transition-all duration-150",
                  lang === l
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-300"
                )}
              >
                {l}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── User + collapse ───────────────────────────────────────────────── */}
      <div className="border-t border-white/[0.06] p-3 space-y-1">
        {!collapsed && (
          <div className="flex items-center gap-2.5 px-2 py-2 rounded-xl hover:bg-white/[0.04] transition-colors cursor-pointer group">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-[11px] font-bold text-white shrink-0 shadow-md shadow-indigo-900/40">
              HR
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-semibold text-slate-300 truncate leading-none">HR Manager</p>
              <p className="text-[10px] text-slate-600 mt-0.5 truncate">AI Analyzer</p>
            </div>
            <Settings className="w-3.5 h-3.5 text-slate-700 group-hover:text-slate-400 transition-colors shrink-0" />
          </div>
        )}

        <button
          onClick={() => setCollapsed((c) => !c)}
          className={cn(
            "w-full flex items-center gap-2 rounded-xl py-2 px-3",
            "text-slate-600 hover:text-slate-300 hover:bg-white/[0.05]",
            "transition-all text-[11px] font-medium",
            collapsed && "justify-center px-0"
          )}
        >
          {collapsed
            ? <ChevronRight className="w-3.5 h-3.5" />
            : <><ChevronLeft className="w-3.5 h-3.5" /><span>{t("collapse") || "Collapse"}</span></>
          }
        </button>
      </div>
    </aside>
  );
}

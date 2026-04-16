// src/components/layout/AppLayout.jsx
import { useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import {
  LayoutDashboard, Briefcase, Mic, Brain,
  FileText, Users, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const ROUTES = [
  { pattern: /^\/$/, icon: LayoutDashboard, label: "Dashboard", section: null },
  { pattern: /^\/jobs/, icon: Briefcase, label: "Jobs", section: "Recruitment" },
  { pattern: /^\/interviews\/[^/]+\/candidates\/[^/]+\/report/, icon: FileText, label: "Candidate Report", section: "Interviews" },
  { pattern: /^\/interviews\/(?!new)[^/]+/, icon: Mic, label: "Interview Detail", section: "Interviews" },
  { pattern: /^\/interviews/, icon: Mic, label: "Interviews", section: "Recruitment" },
  { pattern: /^\/softskills/, icon: Brain, label: "Soft Skills Bank", section: "Settings" },
];

function TopBar() {
  const { pathname } = useLocation();
  const match = ROUTES.find((r) => r.pattern.test(pathname));
  const Icon  = match?.icon ?? LayoutDashboard;
  const label = match?.label ?? "";
  const section = match?.section;

  return (
    <header className="h-13 flex items-center px-6 bg-white border-b border-slate-100 shrink-0 gap-2">
      <div className="flex items-center gap-2 text-slate-400">
        {section && (
          <>
            <span className="text-xs text-slate-400">{section}</span>
            <ChevronRight className="w-3 h-3" />
          </>
        )}
        <Icon className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-xs font-semibold text-slate-600">{label}</span>
      </div>
    </header>
  );
}

export default function AppLayout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 max-w-7xl mx-auto animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

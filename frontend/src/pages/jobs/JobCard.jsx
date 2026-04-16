// src/pages/jobs/JobCard.jsx
import { Briefcase, Building2, Calendar, Pencil, Trash2, Eye } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import LevelBadge from "./LevelBadge";
import { cn } from "@/lib/utils";

const COMPANY_COLORS = [
  "from-indigo-500 to-violet-600",
  "from-sky-500 to-indigo-500",
  "from-emerald-500 to-teal-600",
  "from-amber-500 to-orange-500",
  "from-rose-500 to-pink-600",
  "from-violet-500 to-purple-600",
];

function getCompanyColor(name = "") {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return COMPANY_COLORS[Math.abs(hash) % COMPANY_COLORS.length];
}

export default function JobCard({ job, onView, onEdit, onDelete }) {
  const gradient = getCompanyColor(job.company);
  const initials  = job.company
    ?.split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("") || "?";

  return (
    <div
      onClick={() => onView(job)}
      className={cn(
        "group relative bg-white rounded-2xl border border-slate-200/80 p-5 cursor-pointer",
        "shadow-[0_1px_4px_rgba(0,0,0,0.04)] hover:shadow-[0_8px_24px_rgba(0,0,0,0.08)]",
        "hover:border-slate-300 transition-all duration-200 overflow-hidden"
      )}
    >
      {/* Subtle top gradient strip */}
      <div className={cn("absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity", gradient)} />

      {/* Company logo + actions */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className={cn(
          "w-11 h-11 rounded-xl bg-gradient-to-br flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-sm",
          gradient
        )}>
          {initials}
        </div>

        {/* Action buttons — visible on hover */}
        <div
          className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => onView(job)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
            title="View details"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onEdit(job)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            title="Edit"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(job)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
            title="Delete"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Job info */}
      <div className="space-y-1 mb-3">
        <p className="text-sm font-semibold text-slate-900 leading-snug line-clamp-2 group-hover:text-indigo-900 transition-colors">
          {job.title}
        </p>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Building2 className="w-3 h-3 shrink-0" />
          <span className="truncate">{job.company}</span>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between gap-2 pt-3 border-t border-slate-50">
        <LevelBadge level={job.seniority_level} />
        {job.created_at && (
          <div className="flex items-center gap-1 text-[11px] text-slate-400">
            <Calendar className="w-3 h-3" />
            {format(new Date(job.created_at), "MMM d, yyyy")}
          </div>
        )}
      </div>
    </div>
  );
}

export function JobCardSkeleton() {
  return Array.from({ length: 6 }).map((_, i) => (
    <div key={i} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
      <div className="flex items-start justify-between mb-4">
        <Skeleton className="w-11 h-11 rounded-xl shrink-0" />
      </div>
      <div className="space-y-2 mb-4">
        <Skeleton className="h-4 w-3/4 rounded" />
        <Skeleton className="h-3 w-1/2 rounded" />
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-slate-50">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-3 w-20 rounded" />
      </div>
    </div>
  ));
}

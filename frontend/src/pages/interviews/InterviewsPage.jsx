// src/pages/interviews/InterviewsPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useInterviews, useDeleteInterview } from "../../hooks/useInterviews";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Mic, Briefcase, Trash2, ArrowRight,
  Plus, Code2, Users, Layers, Search, X,
  HelpCircle, Calendar, FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { toast } from "sonner";
import { useI18n } from "@/lib/i18n";

const TYPE_CONFIG = {
  behavioral: {
    label: "Behavioral", icon: Users,
    bg: "bg-blue-50",    text: "text-blue-700",    border: "border-blue-200",
    dot: "bg-blue-400",  strip: "bg-blue-500",
  },
  technical: {
    label: "Technical", icon: Code2,
    bg: "bg-violet-50",  text: "text-violet-700",  border: "border-violet-200",
    dot: "bg-violet-400",strip: "bg-violet-500",
  },
  hr: {
    label: "HR", icon: Briefcase,
    bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200",
    dot: "bg-emerald-400",strip: "bg-emerald-500",
  },
  mixed: {
    label: "Mixed", icon: Layers,
    bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-200",
    dot: "bg-amber-400", strip: "bg-amber-500",
  },
};

// ── Single interview card ─────────────────────────────────────────────────────
function InterviewCard({ interview, onDelete }) {
  const navigate = useNavigate();
  const cfg  = TYPE_CONFIG[interview.type] ?? TYPE_CONFIG.behavioral;
  const Icon = cfg.icon;
  const qCount = interview.questions?.length ?? 0;

  return (
    <div
      onClick={() => navigate(`/interviews/${interview.id}`)}
      className={cn(
        "group relative bg-white rounded-2xl border border-slate-200/80 p-5 cursor-pointer overflow-hidden",
        "shadow-[0_1px_4px_rgba(0,0,0,0.04)] hover:shadow-[0_8px_24px_rgba(0,0,0,0.08)]",
        "hover:border-slate-300 transition-all duration-200"
      )}
    >
      {/* Type accent strip */}
      <div className={cn("absolute top-0 left-0 right-0 h-[3px]", cfg.strip)} />

      <div className="flex items-start justify-between gap-3 pt-1">
        {/* Icon + type */}
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-10 h-10 rounded-xl flex items-center justify-center shrink-0",
            cfg.bg, cfg.border, "border"
          )}>
            <Icon className={cn("w-4 h-4", cfg.text)} />
          </div>
          <div>
            <span className={cn(
              "inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full border capitalize",
              cfg.bg, cfg.text, cfg.border
            )}>
              <span className={cn("w-1.5 h-1.5 rounded-full", cfg.dot)} />
              {cfg.label}
            </span>
          </div>
        </div>

        {/* Delete button */}
        <button
          className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition-all opacity-0 group-hover:opacity-100 shrink-0"
          onClick={(e) => { e.stopPropagation(); onDelete(interview.id); }}
          title="Delete interview"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Title + notes */}
      <div className="mt-3.5 mb-4">
        <h3 className="text-sm font-semibold text-slate-900 line-clamp-2 leading-snug group-hover:text-indigo-900 transition-colors">
          {interview.title}
        </h3>
        {interview.notes && (
          <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">{interview.notes}</p>
        )}
      </div>

      {/* Footer metadata */}
      <div className="flex items-center justify-between gap-2 pt-3 border-t border-slate-50">
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <HelpCircle className="w-3 h-3" />
            {qCount} {qCount === 1 ? "question" : "questions"}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {format(new Date(interview.created_at), "MMM d, yyyy")}
          </span>
        </div>
        <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all" />
      </div>
    </div>
  );
}

// ── Skeleton card ─────────────────────────────────────────────────────────────
function InterviewSkeleton() {
  return Array.from({ length: 6 }).map((_, i) => (
    <div key={i} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
      <div className="absolute top-0 left-0 right-0 h-[3px] bg-slate-100 rounded-t-2xl" />
      <div className="flex items-center gap-3 mb-4">
        <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="h-4 w-3/4 rounded mb-2" />
      <Skeleton className="h-3 w-1/2 rounded mb-4" />
      <div className="flex items-center gap-3 pt-3 border-t border-slate-50">
        <Skeleton className="h-3 w-16 rounded" />
        <Skeleton className="h-3 w-20 rounded" />
      </div>
    </div>
  ));
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function InterviewsPage() {
  const navigate = useNavigate();
  const { data: interviews = [], isLoading, isError } = useInterviews();
  const deleteInterview = useDeleteInterview();
  const { t } = useI18n();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");

  const handleDelete = async (id) => {
    try {
      await deleteInterview.mutateAsync(id);
      toast.success("Interview deleted");
    } catch {
      toast.error("Failed to delete interview");
    }
  };

  const filtered = interviews.filter((iv) => {
    const q = search.toLowerCase();
    const matchSearch = iv.title.toLowerCase().includes(q) || (iv.notes ?? "").toLowerCase().includes(q);
    const matchType   = typeFilter === "all" || iv.type === typeFilter;
    return matchSearch && matchType;
  });

  const counts = interviews.reduce((acc, iv) => {
    acc[iv.type] = (acc[iv.type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{t("interviewsTitle")}</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {isLoading ? t("loading") : `${filtered.length} of ${interviews.length} ${t("interviewCountLabel")}`}
          </p>
        </div>
        <button
          onClick={() => navigate("/interviews/new")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors shadow-sm shadow-indigo-200 shrink-0"
        >
          <Plus className="w-4 h-4" />
          {t("newInterview")}
        </button>
      </div>

      {/* ── Filters ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search interviews…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-8 h-9 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 transition-colors"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Type pills */}
        <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-xl p-1">
          <button
            onClick={() => setTypeFilter("all")}
            className={cn(
              "px-3 py-1 rounded-lg text-xs font-medium transition-all",
              typeFilter === "all" ? "bg-slate-900 text-white shadow-sm" : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
            )}
          >
            All
          </button>
          {Object.entries(TYPE_CONFIG).map(([type, cfg]) => {
            const count = counts[type] || 0;
            if (!count) return null;
            return (
              <button
                key={type}
                onClick={() => setTypeFilter(type)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all capitalize",
                  typeFilter === type
                    ? cn(cfg.bg, cfg.text, "shadow-sm")
                    : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
                )}
              >
                <span className={cn("w-1.5 h-1.5 rounded-full", cfg.dot)} />
                {cfg.label}
                <span className={cn(
                  "text-[10px] font-bold px-1 py-0.5 rounded-full",
                  typeFilter === type ? cn(cfg.bg, cfg.text) : "text-slate-400"
                )}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────────────── */}
      {isError ? (
        <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-slate-200">
          <p className="text-sm text-slate-500">{t("failedLoadInterviews")}</p>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <InterviewSkeleton />
        </div>
      ) : !filtered.length ? (
        <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-slate-200">
          <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center mb-3">
            <Mic className="w-5 h-5 text-slate-300" />
          </div>
          {interviews.length === 0 ? (
            <>
              <p className="text-sm font-semibold text-slate-700">{t("noInterviewsYet")}</p>
              <p className="text-xs text-slate-400 mt-1 mb-5">{t("openJobCreateInterview")}</p>
              <button
                onClick={() => navigate("/interviews/new")}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t("newInterview")}
              </button>
            </>
          ) : (
            <>
              <p className="text-sm font-semibold text-slate-700">No results found</p>
              <button
                onClick={() => { setSearch(""); setTypeFilter("all"); }}
                className="text-xs text-indigo-500 hover:text-indigo-700 mt-2 font-medium transition-colors"
              >
                Clear filters
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((iv) => (
            <InterviewCard key={iv.id} interview={iv} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

// src/pages/jobs/JobsPage.jsx
import { useState } from "react";
import { useJobs } from "../../hooks/useJobs";
import { Button } from "@/components/ui/button";
import { Briefcase, Plus, X, Search, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import JobCard, { JobCardSkeleton } from "./JobCard";
import JobFormDialog from "./JobFormDialog";
import DeleteDialog from "./DeleteDialog";
import JobSheet from "./JobSheet";
import { useI18n } from "@/lib/i18n";

const LEVELS = ["all", "junior", "mid", "senior", "lead"];

const LEVEL_DOTS = {
  junior: "bg-sky-400",
  mid:    "bg-violet-400",
  senior: "bg-amber-400",
  lead:   "bg-rose-400",
};

export default function JobsPage() {
  const { data: jobs = [], isLoading, isError } = useJobs();
  const { t } = useI18n();

  const [viewJob,     setViewJob]     = useState(null);
  const [editJob,     setEditJob]     = useState(null);
  const [deleteJob,   setDeleteJob]   = useState(null);
  const [showCreate,  setShowCreate]  = useState(false);
  const [search,      setSearch]      = useState("");
  const [levelFilter, setLevelFilter] = useState("all");

  const filtered = jobs.filter((job) => {
    const q = search.toLowerCase();
    const matchSearch =
      job.title.toLowerCase().includes(q) ||
      job.company.toLowerCase().includes(q);
    const matchLevel = levelFilter === "all" || job.seniority_level === levelFilter;
    return matchSearch && matchLevel;
  });

  return (
    <div className="space-y-6">

      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{t("jobsTitle")}</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {isLoading
              ? t("loading")
              : `${filtered.length} ${t("of")} ${jobs.length} ${t("positionsLabel")}`}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors shadow-sm shadow-indigo-200 shrink-0"
        >
          <Plus className="w-4 h-4" />
          {t("addJob")}
        </button>
      </div>

      {/* ── Filters ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-48 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <Input
            placeholder={t("searchTitleCompany")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9 text-sm bg-white border-slate-200 focus:border-indigo-300 focus:ring-indigo-200"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 hover:text-slate-600 flex items-center justify-center"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Level filter pills */}
        <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-xl p-1">
          {LEVELS.map((lvl) => (
            <button
              key={lvl}
              onClick={() => setLevelFilter(lvl)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all",
                levelFilter === lvl
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
              )}
            >
              {lvl !== "all" && (
                <span className={cn("w-1.5 h-1.5 rounded-full", LEVEL_DOTS[lvl])} />
              )}
              {lvl === "all" ? t("allLevels") : lvl}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────────────── */}
      {isError ? (
        <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-slate-200">
          <div className="w-12 h-12 rounded-2xl bg-red-50 flex items-center justify-center mb-3">
            <X className="w-5 h-5 text-red-400" />
          </div>
          <p className="text-sm font-semibold text-slate-700">{t("failedLoadJobs")}</p>
          <p className="text-xs text-slate-400 mt-1">{t("checkConnection")}</p>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <JobCardSkeleton />
        </div>
      ) : !filtered.length ? (
        <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-slate-200">
          <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center mb-3">
            <Briefcase className="w-5 h-5 text-slate-300" />
          </div>
          {jobs.length === 0 ? (
            <>
              <p className="text-sm font-semibold text-slate-700">{t("noJobsYet")}</p>
              <p className="text-xs text-slate-400 mt-1 mb-5">{t("addFirstJob")}</p>
              <button
                onClick={() => setShowCreate(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t("addJob")}
              </button>
            </>
          ) : (
            <>
              <p className="text-sm font-semibold text-slate-700">{t("noResultsFound")}</p>
              <p className="text-xs text-slate-400 mt-1">{t("adjustSearchFilter")}</p>
              <button
                onClick={() => { setSearch(""); setLevelFilter("all"); }}
                className="text-xs text-indigo-500 hover:text-indigo-700 mt-3 font-medium transition-colors"
              >
                {t("clearFilters")}
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onView={setViewJob}
              onEdit={setEditJob}
              onDelete={setDeleteJob}
            />
          ))}
        </div>
      )}

      {/* ── Modals ──────────────────────────────────────────────────────── */}
      <JobFormDialog open={showCreate}  onClose={() => setShowCreate(false)} />
      <JobFormDialog open={!!editJob}   onClose={() => setEditJob(null)} initial={editJob} />
      <DeleteDialog  job={deleteJob}    open={!!deleteJob} onClose={() => setDeleteJob(null)} />
      <JobSheet
        job={viewJob}
        open={!!viewJob}
        onClose={() => setViewJob(null)}
        onEdit={(job) => { setViewJob(null); setEditJob(job); }}
      />
    </div>
  );
}

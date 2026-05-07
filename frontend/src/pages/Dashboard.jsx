// src/pages/Dashboard.jsx
import { useNavigate } from "react-router-dom";
import { useJobs } from "../hooks/useJobs";
import { useInterviews, useDashboardSummary } from "../hooks/useInterviews";
import {
  Briefcase, Mic, Users, Clock,
  ArrowRight, Plus, Sparkles, ChevronRight,
  Layers, CheckCircle2, AlertCircle, XCircle,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { useI18n } from "@/lib/i18n";

const INTERVIEW_TYPE_COLOR = {
  behavioral: { bg: "bg-blue-100",    text: "text-blue-700"    },
  technical:  { bg: "bg-violet-100",  text: "text-violet-700"  },
  hr:         { bg: "bg-emerald-100", text: "text-emerald-700" },
  mixed:      { bg: "bg-amber-100",   text: "text-amber-700"   },
};

const DECISION_CFG = {
  PROCEED: { icon: CheckCircle2, bg: "bg-emerald-50",  text: "text-emerald-700", badge: "bg-emerald-500", labelKey: "decisionProceed" },
  REVIEW:  { icon: AlertCircle,  bg: "bg-amber-50",    text: "text-amber-700",   badge: "bg-amber-500",   labelKey: "decisionReview"  },
  REJECT:  { icon: XCircle,      bg: "bg-red-50",      text: "text-red-700",     badge: "bg-red-500",     labelKey: "decisionReject"  },
};

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, gradient, loading, onClick }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative bg-white rounded-2xl border border-slate-200/80 p-5 text-left",
        "shadow-[0_1px_4px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_20px_rgba(0,0,0,0.08)]",
        "transition-all duration-200 overflow-hidden w-full",
        onClick && "cursor-pointer"
      )}
    >
      <div className={cn(
        "absolute -top-6 -right-6 w-24 h-24 rounded-full opacity-10 blur-xl transition-opacity group-hover:opacity-20",
        gradient
      )} />

      <div className="flex items-start justify-between gap-3 relative">
        <div className={cn(
          "w-10 h-10 rounded-xl flex items-center justify-center shrink-0",
          gradient, "bg-opacity-15"
        )}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        {onClick && (
          <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-500 transition-colors shrink-0 mt-0.5" />
        )}
      </div>

      <div className="mt-4 relative">
        {loading ? (
          <Skeleton className="h-9 w-14 rounded-lg mb-1" />
        ) : (
          <p className="text-3xl font-bold text-slate-900 tabular-nums leading-none tracking-tight">
            {value ?? "—"}
          </p>
        )}
        <p className="text-sm font-medium text-slate-600 mt-1.5">{label}</p>
        {sub && !loading && (
          <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
        )}
      </div>
    </button>
  );
}

// ── Interview type distribution ───────────────────────────────────────────────
function InterviewTypeBadges({ interviews }) {
  const counts = interviews.reduce((acc, iv) => {
    acc[iv.type] = (acc[iv.type] || 0) + 1;
    return acc;
  }, {});

  const types = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!types.length) return <p className="text-xs text-slate-400">—</p>;

  return (
    <div className="flex flex-wrap gap-2">
      {types.map(([type, count]) => {
        const cfg = INTERVIEW_TYPE_COLOR[type] ?? { bg: "bg-slate-100", text: "text-slate-600" };
        return (
          <div key={type} className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium capitalize", cfg.bg, cfg.text)}>
            <Layers className="w-3 h-3" />
            {type} · {count}
          </div>
        );
      })}
    </div>
  );
}

// ── Recent activity feed ──────────────────────────────────────────────────────
function RecentActivity({ items, loading, t, lang, onNavigate }) {
  if (loading) {
    return (
      <div className="space-y-3 px-5 py-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="w-8 h-8 rounded-full shrink-0" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-32 rounded" />
              <Skeleton className="h-3 w-20 rounded" />
            </div>
            <Skeleton className="h-5 w-16 rounded-full shrink-0" />
          </div>
        ))}
      </div>
    );
  }

  if (!items?.length) {
    return (
      <div className="px-5 py-8 text-center">
        <p className="text-xs text-slate-400">{t("noCandidatesAnalysed")}</p>
      </div>
    );
  }

  const locale = lang === "fr" ? dateFnsFr : undefined;

  return (
    <div className="px-5 py-3 space-y-1">
      {items.map((item) => {
        const dcfg = DECISION_CFG[item.decision] || DECISION_CFG.REVIEW;
        const DecIcon = dcfg.icon;
        return (
          <div
            key={item.id}
            className="group flex items-center gap-3 py-2.5 border-b border-slate-50 last:border-0"
          >
            <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0", dcfg.badge)}>
              <DecIcon className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{item.candidate_name}</p>
              <p className="text-xs text-slate-400 truncate">{item.interview_title}</p>
            </div>
            <div className="flex flex-col items-end gap-0.5 shrink-0">
              <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", dcfg.bg, dcfg.text)}>
                {t(dcfg.labelKey)}
              </span>
              {item.overall_score > 0 && (
                <span className="text-[10px] text-slate-400 tabular-nums">{Math.round(item.overall_score)}/100</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Recent job row ────────────────────────────────────────────────────────────
function JobRow({ job }) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate("/jobs")}
      className="group w-full flex items-center gap-3 py-3 border-b border-slate-50 last:border-0 hover:bg-slate-50/80 -mx-2 px-2 rounded-lg transition-colors"
    >
      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold bg-slate-100 text-slate-600">
        {job.company?.[0]?.toUpperCase() ?? "?"}
      </div>
      <div className="flex-1 min-w-0 text-left">
        <p className="text-sm font-medium text-slate-800 truncate group-hover:text-slate-900">{job.title}</p>
        <p className="text-xs text-slate-400 truncate">{job.company}</p>
      </div>
      {job.created_at && (
        <span className="text-[11px] text-slate-400 hidden sm:block shrink-0">
          {format(new Date(job.created_at), "MMM d")}
        </span>
      )}
    </button>
  );
}

// ── Quick action card ─────────────────────────────────────────────────────────
function QuickAction({ icon: Icon, label, description, onClick, gradient }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group w-full flex items-center gap-3.5 p-3.5 rounded-xl border text-left",
        "bg-white border-slate-200 hover:border-indigo-200 hover:bg-indigo-50/40",
        "shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:shadow-[0_2px_8px_rgba(99,102,241,0.1)]",
        "transition-all duration-150"
      )}
    >
      <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center shrink-0", gradient)}>
        <Icon className="w-4 h-4 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800 group-hover:text-slate-900">{label}</p>
        <p className="text-xs text-slate-400 mt-0.5">{description}</p>
      </div>
      <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all shrink-0" />
    </button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { data: jobs = [],       isLoading: loadingJobs }       = useJobs();
  const { data: interviews = [], isLoading: loadingInterviews } = useInterviews();
  const { data: summary,         isLoading: loadingSummary }    = useDashboardSummary();
  const navigate = useNavigate();
  const { t, lang } = useI18n();

  const loading = loadingJobs || loadingInterviews;
  const recentJobs     = [...jobs].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 6);
  const processedCount = interviews.reduce((sum, iv) => sum + (iv.processed_count || 0), 0);
  const pendingCount   = summary?.pending_count ?? 0;

  const dateLabel = new Date().toLocaleDateString(
    lang === "fr" ? "fr-FR" : "en-US",
    { weekday: "long", month: "long", day: "numeric", year: "numeric" }
  );

  return (
    <div className="space-y-6">

      {/* ── Welcome header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-6 h-6 rounded-lg bg-linear-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
            <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">AI Analyzer</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{t("dashboardTitle")}</h1>
          <p className="text-sm text-slate-400 mt-0.5 capitalize">{dateLabel}</p>
        </div>
        <button
          onClick={() => navigate("/jobs")}
          className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors shadow-sm shadow-indigo-200"
        >
          <Plus className="w-4 h-4" />
          {t("addJob")}
        </button>
      </div>

      {/* ── Stats row ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Briefcase}
          label={t("totalJobs")}
          value={jobs.length}
          gradient="bg-indigo-600"
          loading={loadingJobs}
          onClick={() => navigate("/jobs")}
        />
        <StatCard
          icon={Mic}
          label={t("interviews")}
          value={interviews.length}
          gradient="bg-sky-500"
          loading={loadingInterviews}
          onClick={() => navigate("/interviews")}
        />
        <StatCard
          icon={Clock}
          label={t("pendingReview")}
          value={pendingCount}
          sub={t("awaitingAnalysis")}
          gradient="bg-amber-500"
          loading={loadingSummary}
          onClick={() => navigate("/interviews")}
        />
        <StatCard
          icon={Users}
          label={t("processed")}
          value={processedCount}
          sub={t("candidateAnalysesDone")}
          gradient="bg-emerald-500"
          loading={loading}
        />
      </div>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* Recent Jobs — 3 cols */}
        <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">{t("recentJobs")}</h2>
              <p className="text-xs text-slate-400 mt-0.5">{t("latestPositions")}</p>
            </div>
            <button
              onClick={() => navigate("/jobs")}
              className="flex items-center gap-1 text-xs font-medium text-indigo-500 hover:text-indigo-700 transition-colors"
            >
              {t("viewAll")}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="px-5 py-3">
            {loadingJobs ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 py-3 border-b border-slate-50 last:border-0">
                  <Skeleton className="w-8 h-8 rounded-lg shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3.5 w-36 rounded" />
                    <Skeleton className="h-3 w-24 rounded" />
                  </div>
                </div>
              ))
            ) : !recentJobs.length ? (
              <div className="py-10 text-center">
                <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center mx-auto mb-3">
                  <Briefcase className="w-5 h-5 text-slate-300" />
                </div>
                <p className="text-sm text-slate-500 font-medium">{t("noJobsYet")}</p>
                <button
                  onClick={() => navigate("/jobs")}
                  className="text-xs text-indigo-500 hover:text-indigo-700 mt-1.5 font-medium transition-colors"
                >
                  {t("addFirstJob")} →
                </button>
              </div>
            ) : (
              recentJobs.map((job) => <JobRow key={job.id} job={job} />)
            )}
          </div>
        </div>

        {/* Right column — 2 cols */}
        <div className="lg:col-span-2 flex flex-col gap-5">

          {/* Recent Activity */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">{t("recentActivity")}</h2>
                <p className="text-xs text-slate-400 mt-0.5">{t("latestAnalyses")}</p>
              </div>
              <button
                onClick={() => navigate("/interviews")}
                className="flex items-center gap-1 text-xs font-medium text-indigo-500 hover:text-indigo-700 transition-colors"
              >
                {t("viewAll")}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <RecentActivity
              items={summary?.recent_processed}
              loading={loadingSummary}
              t={t}
              lang={lang}
              onNavigate={navigate}
            />
          </div>

          {/* Interview types */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-900">{t("interviews")}</h2>
              <p className="text-xs text-slate-400 mt-0.5">{t("allTypes")}</p>
            </div>
            <div className="px-5 py-4">
              {loadingInterviews ? (
                <div className="flex gap-2 flex-wrap">
                  {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-7 w-24 rounded-xl" />)}
                </div>
              ) : (
                <InterviewTypeBadges interviews={interviews} />
              )}
            </div>
          </div>

          {/* Quick actions */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-900">{t("addJob")}</h2>
            </div>
            <div className="p-4 space-y-2">
              <QuickAction
                icon={Briefcase}
                label={t("addJob")}
                description={lang === "fr" ? "Publier une nouvelle offre" : "Post a new position"}
                gradient="bg-linear-to-br from-indigo-500 to-violet-600"
                onClick={() => navigate("/jobs")}
              />
              <QuickAction
                icon={Mic}
                label={t("newInterview")}
                description={lang === "fr" ? "Configurer une session d'entretien" : "Set up an interview session"}
                gradient="bg-linear-to-br from-sky-500 to-indigo-500"
                onClick={() => navigate("/interviews")}
              />
              <QuickAction
                icon={Clock}
                label={lang === "fr" ? "Examiner les candidats" : "Review Candidates"}
                description={lang === "fr" ? "Consulter les rapports traites" : "Check processed reports"}
                gradient="bg-linear-to-br from-emerald-500 to-teal-500"
                onClick={() => navigate("/interviews")}
              />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

// src/pages/jobs/JobSheet.jsx
import { useNavigate } from "react-router-dom";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { Button }   from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Briefcase, Building2, Pencil, Calendar,
  RefreshCw, Plus, ArrowRight, Mic,
} from "lucide-react";
import { format } from "date-fns";
import LevelBadge from "./LevelBadge";
import { useInterviewByJob } from "../../hooks/useInterviews";
import { cn } from "@/lib/utils";

const TYPE_STYLES = {
  behavioral: "bg-blue-50   text-blue-700   border-blue-200",
  technical:  "bg-violet-50 text-violet-700 border-violet-200",
  hr:         "bg-emerald-50 text-emerald-700 border-emerald-200",
  mixed:      "bg-amber-50  text-amber-700  border-amber-200",
};

export default function JobSheet({ job, open, onClose, onEdit }) {
  const navigate = useNavigate();
  const { data: interview, isLoading: loadingInterview } = useInterviewByJob(job?.id);
  const hasInterview = !!interview;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      {/* Fixed-size dialog — never scrolls as a whole */}
      <DialogContent
        className="sm:max-w-[900px] p-0 overflow-hidden"
        style={{ height: "600px", display: "flex", flexDirection: "column" }}
      >

        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="px-6 pt-5 pb-4 border-b border-slate-100 shrink-0">
          <div className="flex items-start gap-4">
            <div className="w-9 h-9 rounded-xl bg-slate-900 flex items-center justify-center shrink-0">
              <Briefcase className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <DialogTitle className="text-base font-semibold text-slate-900 leading-tight">
                {job?.title}
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-400 mt-0.5 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 shrink-0" />
                {job?.company}
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <LevelBadge level={job?.seniority_level} />
              <Button variant="outline" size="sm" className="h-7 px-2.5 text-xs gap-1.5"
                onClick={() => { onClose(); onEdit(job); }}>
                <Pencil className="w-3 h-3" /> Edit
              </Button>
            </div>
          </div>

          <div className="flex gap-4 flex-wrap mt-3">
            {job?.created_at && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Calendar className="w-3.5 h-3.5" />
                Added {format(new Date(job.created_at), "MMMM d, yyyy")}
              </div>
            )}
            {job?.updated_at && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <RefreshCw className="w-3.5 h-3.5" />
                Updated {format(new Date(job.updated_at), "MMM d, yyyy")}
              </div>
            )}
          </div>
        </div>

        {/* ── Body: two columns, fills remaining height ───────────── */}
        <div className="flex min-h-0 flex-1">

          {/* LEFT — two independently-scrollable sections stacked */}
          <div className="flex flex-col flex-1 min-w-0 min-h-0 divide-y divide-slate-100">

            {/* Description — scrollable */}
            <div className="flex flex-col flex-1 min-h-0 px-6 py-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 shrink-0">
                Job Description
              </p>
              <div className="flex-1 overflow-y-auto rounded-xl bg-slate-50 border border-slate-100 px-4 py-3">
                {job?.description
                  ? <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{job.description}</p>
                  : <p className="text-sm text-slate-400 italic">No description provided.</p>
                }
              </div>
            </div>

            {/* Requirements — scrollable */}
            <div className="flex flex-col flex-1 min-h-0 px-6 py-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 shrink-0">
                Requirements
              </p>
              <div className="flex-1 overflow-y-auto rounded-xl bg-slate-50 border border-slate-100 px-4 py-3">
                {job?.requirements
                  ? <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{job.requirements}</p>
                  : <p className="text-sm text-slate-400 italic">No requirements listed.</p>
                }
              </div>
            </div>

          </div>

          {/* RIGHT — interview panel, fixed width, static */}
          <div
            className="shrink-0 flex flex-col px-5 py-5 bg-slate-50/70 border-l border-slate-100"
            style={{ width: "260px" }}
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Interview
            </p>

            {loadingInterview ? (
              <div className="space-y-2">
                <Skeleton className="h-5 w-3/4 rounded" />
                <Skeleton className="h-4 w-1/2 rounded" />
                <Skeleton className="h-8 w-full rounded-lg mt-3" />
              </div>

            ) : hasInterview ? (
              <div className="flex flex-col gap-3">
                <div className="bg-white rounded-xl border border-slate-200 p-3.5 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-slate-900 leading-tight">{interview.title}</p>
                    <span className={cn(
                      "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border capitalize shrink-0",
                      TYPE_STYLES[interview.type] ?? "bg-slate-50 text-slate-500 border-slate-200"
                    )}>
                      {interview.type}
                    </span>
                  </div>
                  {interview.notes && (
                    <p className="text-xs text-slate-500 line-clamp-2">{interview.notes}</p>
                  )}
                  <p className="text-[11px] text-slate-400">
                    Created {format(new Date(interview.created_at), "MMM d, yyyy")}
                  </p>
                </div>
                <Button size="sm"
                  onClick={() => { onClose(); navigate(`/interviews/${interview.id}`); }}
                  className="w-full bg-slate-900 hover:bg-slate-700 text-white gap-1.5 text-xs">
                  <Mic className="w-3.5 h-3.5" />
                  Open Interview
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </div>

            ) : (
              <div className="flex flex-col items-center text-center gap-3 pt-6">
                <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center">
                  <Mic className="w-4 h-4 text-slate-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-700">No interview yet</p>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                    Create an interview session for this job
                  </p>
                </div>
                <Button size="sm"
                  onClick={() => {
                    onClose();
                    navigate(`/interviews/new?job_id=${job.id}&job_title=${encodeURIComponent(job.title)}`);
                  }}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5 text-xs h-8">
                  <Plus className="w-3.5 h-3.5" />
                  Create Interview
                </Button>
              </div>
            )}
          </div>

        </div>
      </DialogContent>
    </Dialog>
  );
}
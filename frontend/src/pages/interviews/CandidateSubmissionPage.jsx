// src/pages/interviews/CandidateSubmissionPage.jsx
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  Upload, FileVideo, CheckCircle2, Sparkles,
  Video, HelpCircle, AlertCircle, Loader2, Clock,
  CheckCircle, XCircle,
} from "lucide-react";
import {
  useCandidateAccess, useSubmitCandidateVideo,
} from "../../hooks/useInterviews";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const DECISION_CFG = {
  PROCEED: { icon: CheckCircle, color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", labelKey: "decisionProceed" },
  REVIEW:  { icon: AlertCircle, color: "text-amber-600",   bg: "bg-amber-50",   border: "border-amber-200",   labelKey: "decisionReview"  },
  REJECT:  { icon: XCircle,     color: "text-rose-600",    bg: "bg-rose-50",    border: "border-rose-200",    labelKey: "decisionReject"  },
};

export default function CandidateSubmissionPage() {
  const { token }       = useParams();
  const { data, isLoading, isError } = useCandidateAccess(token);
  const submitVideo     = useSubmitCandidateVideo(token);
  const { t, tv } = useI18n();

  const [file,     setFile]     = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const canSubmit = useMemo(() => {
    if (!data) return false;
    return ["assigned", "submitted", "failed"].includes(data.status);
  }, [data]);

  const onSubmit = async () => {
    if (!file) { toast.error("Please choose a video file first."); return; }
    try {
      const result = await submitVideo.mutateAsync(file);
      setAnalysis(result.analysis || null);
      toast.success("Video submitted and processed successfully.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to submit video.");
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.type.startsWith("video/")) setFile(dropped);
    else toast.error("Please drop a video file.");
  };

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50/30 flex items-center justify-center p-4">
        <div className="w-full max-w-2xl space-y-4">
          <Skeleton className="h-16 w-64 rounded-2xl mx-auto" />
          <Skeleton className="h-48 w-full rounded-2xl" />
          <Skeleton className="h-40 w-full rounded-2xl" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50/30 flex items-center justify-center p-4">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-rose-100 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-rose-500" />
          </div>
          <h2 className="text-lg font-semibold text-slate-800">{t("invalidLink")}</h2>
          <p className="text-sm text-slate-400 mt-1">This link is invalid or has expired.</p>
        </div>
      </div>
    );
  }

  const dcfg = analysis ? (DECISION_CFG[analysis.decision] ?? DECISION_CFG.REVIEW) : null;
  const DecisionIcon = dcfg?.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/20 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-5">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-xs font-semibold text-indigo-600 mb-2">
            <Sparkles className="w-3 h-3" />
            {t("candidatePortal")}
          </div>
          <h1 className="text-2xl font-bold text-slate-900">{t("interviewSubmission")}</h1>
          <p className="text-sm text-slate-400">
            {t("candidate")}: <span className="font-medium text-slate-600">{data.candidate_name}</span>
            {" · "}
            <span className={cn(
              "inline-flex items-center gap-1 font-medium",
              data.status === "processed" ? "text-emerald-600" :
              data.status === "submitted" ? "text-blue-600" :
              data.status === "failed"    ? "text-rose-600" : "text-slate-500"
            )}>
              {data.status === "processed" && <CheckCircle2 className="w-3 h-3" />}
              {tv(data.status)}
            </span>
          </p>
        </div>

        {/* ── Interview info ───────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
              <Video className="w-4 h-4 text-indigo-600" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("interview")}</p>
              <p className="text-sm font-semibold text-slate-900">{data.interview_title}</p>
            </div>
          </div>

          <div className="p-5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5" />
              {t("questions")} ({data.questions.length})
            </p>
            <ol className="space-y-2.5">
              {data.questions.map((item, i) => (
                <li key={item.id} className="flex gap-3">
                  <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <p className="text-sm text-slate-700 leading-relaxed">{item.question}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* ── Upload section ───────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100">
            <div className="w-8 h-8 rounded-xl bg-violet-50 flex items-center justify-center">
              <Upload className="w-4 h-4 text-violet-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">{t("uploadInterviewVideo")}</p>
              <p className="text-xs text-slate-400">{t("recordAllAnswers")}</p>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => !submitVideo.isPending && document.getElementById("video-input").click()}
              className={cn(
                "relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-150",
                dragOver
                  ? "border-indigo-400 bg-indigo-50"
                  : file
                  ? "border-emerald-300 bg-emerald-50/40"
                  : "border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30",
                (!canSubmit || submitVideo.isPending) && "opacity-50 pointer-events-none"
              )}
            >
              <input
                id="video-input"
                type="file"
                accept="video/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                disabled={!canSubmit || submitVideo.isPending}
              />
              {file ? (
                <div className="space-y-2">
                  <FileVideo className="w-8 h-8 text-emerald-500 mx-auto" />
                  <p className="text-sm font-semibold text-emerald-700">{file.name}</p>
                  <p className="text-xs text-slate-400">{(file.size / 1024 / 1024).toFixed(1)} MB · {t("clickToChange")}</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="w-8 h-8 text-slate-300 mx-auto" />
                  <p className="text-sm font-medium text-slate-500">
                    {dragOver ? t("dropHere") : t("clickOrDrop")}
                  </p>
                  <p className="text-xs text-slate-400">{t("videoFormats")}</p>
                </div>
              )}
            </div>

            {!canSubmit && (
              <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                {t("submissionClosed")}
              </div>
            )}

            <button
              onClick={onSubmit}
              disabled={!canSubmit || submitVideo.isPending || !file}
              className={cn(
                "w-full flex items-center justify-center gap-2 h-11 rounded-xl text-sm font-semibold transition-all",
                "bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-200",
                "disabled:opacity-50 disabled:pointer-events-none"
              )}
            >
              {submitVideo.isPending ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> {t("processing")}</>
              ) : (
                <><Upload className="w-4 h-4" /> {t("submit")}</>
              )}
            </button>

            {submitVideo.isPending && (
              <div className="flex items-center justify-center gap-2 text-xs text-indigo-600 animate-pulse">
                <Sparkles className="w-3.5 h-3.5" />
                {t("analyzingVideo")}
              </div>
            )}
          </div>
        </div>

        {/* ── Analysis result ──────────────────────────────────────────── */}
        {analysis && dcfg && (
          <div className={cn("rounded-2xl border overflow-hidden shadow-[0_1px_4px_rgba(0,0,0,0.04)]", dcfg.border)}>
            <div className={cn("flex items-center gap-3 px-5 py-4 border-b", dcfg.bg, dcfg.border)}>
              <DecisionIcon className={cn("w-5 h-5 shrink-0", dcfg.color)} />
              <div>
                <p className="text-xs font-semibold text-slate-500">{t("processedResult")}</p>
                <p className={cn("text-sm font-bold", dcfg.color)}>{t(dcfg.labelKey)}</p>
              </div>
              <div className="ml-auto text-right">
                <p className="text-xs text-slate-400">{t("overallScore")}</p>
                <p className="text-2xl font-bold text-slate-900 tabular-nums leading-none">
                  {analysis.overall_score ?? 0}
                  <span className="text-sm font-medium text-slate-400">/100</span>
                </p>
              </div>
            </div>
            <div className="bg-white px-5 py-4">
              <p className="text-sm text-slate-700 leading-relaxed">
                {analysis.hr_summary || t("processedDone")}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// src/pages/interviews/CandidateReportPage.jsx
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useCandidateReport } from "../../hooks/useInterviews";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { useI18n } from "@/lib/i18n";
import {
  ArrowLeft, Brain, Award, CheckCircle2,
  XCircle, AlertCircle, Quote, Clock, Users, BarChart3,
  Smile, Activity, Eye, Zap,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, Legend,
} from "recharts";

// ── Emotion colour palette ────────────────────────────────────────────────────
const EMOTION_COLORS = {
  happy:      "#22c55e",
  neutral:    "#94a3b8",
  surprised:  "#f59e0b",
  fearful:    "#f97316",
  sad:        "#3b82f6",
  angry:      "#ef4444",
  disgusted:  "#a855f7",
};
const EMOTION_EMOJI = {
  happy: "😊", neutral: "😐", surprised: "😲",
  fearful: "😨", sad: "😢", angry: "😠", disgusted: "🤢",
};

// Maps backend emotion keys → i18n translation keys
const EMOTION_KEY_MAP = {
  happy:     "emotionHappy",
  neutral:   "emotionNeutral",
  surprised: "emotionSurprised",
  fearful:   "emotionFearful",
  sad:       "emotionSad",
  angry:     "emotionAngry",
  disgusted: "emotionDisgusted",
};

const CONFIDENCE_KEY_MAP = {
  high:    "confidenceHigh",
  medium:  "confidenceMedium",
  low:     "confidenceLow",
  unknown: "confidenceUnknown",
};

const FOCUS_KEY_MAP = {
  high:   "focusHigh",
  medium: "focusMedium",
  low:    "focusLow",
};

const STRENGTH_KEY_MAP = {
  strong:           "strengthStrong",
  moderate:         "strengthModerate",
  weak:             "strengthWeak",
  not_demonstrated: "strengthNotDemonstrated",
};

// ── Decision config ───────────────────────────────────────────────────────────
const DECISION_CFG = {
  PROCEED: {
    icon: CheckCircle2,
    bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", badge: "bg-emerald-500",
    labelKey: "decisionProceed",
  },
  REVIEW: {
    icon: AlertCircle,
    bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", badge: "bg-amber-500",
    labelKey: "decisionReview",
  },
  REJECT: {
    icon: XCircle,
    bg: "bg-red-50", border: "border-red-200", text: "text-red-700", badge: "bg-red-500",
    labelKey: "decisionReject",
  },
};

const STRENGTH_CFG = {
  strong:           { color: "bg-emerald-100 text-emerald-700 border-emerald-200", bar: "bg-emerald-500", w: "w-full" },
  moderate:         { color: "bg-blue-100 text-blue-700 border-blue-200",           bar: "bg-blue-500",    w: "w-3/4"  },
  weak:             { color: "bg-amber-100 text-amber-700 border-amber-200",        bar: "bg-amber-400",   w: "w-2/4"  },
  not_demonstrated: { color: "bg-slate-100 text-slate-500 border-slate-200",        bar: "bg-slate-300",   w: "w-1/4"  },
};

const FOCUS_CFG = {
  high:   "bg-emerald-100 text-emerald-700 border-emerald-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low:    "bg-red-100 text-red-700 border-red-200",
};

// ── Circular gauge ────────────────────────────────────────────────────────────
function RingGauge({ value, max = 100, size = 96, strokeWidth = 9, color = "#6366f1", label, sub }) {
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(Math.max(value / max, 0), 1);
  const dash = pct * circumference;

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#e2e8f0" strokeWidth={strokeWidth} />
          <circle
            cx={size/2} cy={size/2} r={radius}
            fill="none" stroke={color} strokeWidth={strokeWidth}
            strokeDasharray={`${dash} ${circumference}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.6s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-bold text-slate-900 leading-none tabular-nums">{Math.round(value)}</span>
          {sub && <span className="text-[10px] text-slate-400 mt-0.5">{sub}</span>}
        </div>
      </div>
      {label && <span className="text-xs text-slate-500 text-center leading-tight">{label}</span>}
    </div>
  );
}

// ── Horizontal metric bar ─────────────────────────────────────────────────────
function MetricBar({ label, value, max = 100, color = "bg-indigo-500" }) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-600">{label}</span>
        <span className="text-xs font-semibold text-slate-800 tabular-nums">
          {Math.round(value)}{max === 100 ? "%" : `/${max}`}
        </span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-700", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Section card ──────────────────────────────────────────────────────────────
function Card({ children, className }) {
  return (
    <div className={cn("bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden", className)}>
      {children}
    </div>
  );
}

function CardHeader({ icon: Icon, title, sub, iconColor = "bg-indigo-500" }) {
  return (
    <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100">
      <div className={cn("w-8 h-8 rounded-xl flex items-center justify-center shrink-0", iconColor)}>
        <Icon className="w-4 h-4 text-white" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Custom tooltip for recharts ───────────────────────────────────────────────
function ChartTooltip({ active, payload, label, tEmotion }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-slate-700 mb-1">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-slate-600">{tEmotion ? tEmotion(entry.name) : entry.name}:</span>
          <span className="font-semibold text-slate-800">{Number(entry.value).toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}

// ── Skeleton loading ──────────────────────────────────────────────────────────
function ReportSkeleton() {
  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      <Skeleton className="h-32 w-full rounded-2xl" />
      <Skeleton className="h-28 w-full rounded-2xl" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
      <Skeleton className="h-80 w-full rounded-2xl" />
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CandidateReportPage() {
  const { interviewId, candidateId } = useParams();
  const navigate  = useNavigate();
  const location  = useLocation();
  const state     = location.state || {};
  const { t }     = useI18n();

  // Translate backend emotion key → current-language label
  const tEmotion = (key) => t(EMOTION_KEY_MAP[key]) || key;

  const { data: report, isLoading, isError } = useCandidateReport(interviewId, candidateId, true);

  if (isLoading) {
    return (
      <div className="p-6 space-y-5">
        <button onClick={() => navigate(`/interviews/${interviewId}`)}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 transition-colors">
          <ArrowLeft className="w-4 h-4" /> {t("backToInterview")}
        </button>
        <ReportSkeleton />
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <button onClick={() => navigate(`/interviews/${interviewId}`)}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 transition-colors mb-6">
          <ArrowLeft className="w-4 h-4" /> {t("backToInterview")}
        </button>
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <AlertCircle className="w-12 h-12 text-slate-300 mb-3" />
          <p className="text-slate-500 font-medium">{t("reportNotAvailable")}</p>
          <p className="text-xs text-slate-400 mt-1">{t("analysisProcessing")}</p>
        </div>
      </div>
    );
  }

  const {
    decision = "REVIEW",
    overall_score = 0,
    hr_summary = "",
    decision_reasons = [],
    qa_pairs_count = 0,
    generated_at,
    text_metrics = {},
    detected_skills = [],
    emotion_metrics = {},
    engagement_metrics = {},
  } = report;

  const dcfg = DECISION_CFG[decision] || DECISION_CFG.REVIEW;
  const DecisionIcon = dcfg.icon;

  // ── Chart data ──────────────────────────────────────────────────────────────
  const relevanceData = (text_metrics.relevance_per_question || []).map((score, i) => ({
    name: `Q${i + 1}`,
    score: Number(score.toFixed(1)),
  }));

  const rawTimeline = emotion_metrics.emotion_timeline || [];
  const step = Math.max(1, Math.ceil(rawTimeline.length / 80));
  const timelineData = rawTimeline
    .filter((_, i) => i % step === 0)
    .map((pt) => ({
      t: Number(pt.timestamp_sec?.toFixed(1) ?? 0),
      ...Object.fromEntries(
        Object.entries(pt.emotion_scores ?? {}).map(([k, v]) => [k, Number((v * 100).toFixed(1))])
      ),
    }));

  const timelineKeys = timelineData.length
    ? Object.keys(timelineData[0]).filter((k) => k !== "t")
    : [];

  const dominantEmotion = emotion_metrics.dominant_emotion || "neutral";

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">

      {/* Back */}
      <button onClick={() => navigate(`/interviews/${interviewId}`)}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 transition-colors">
        <ArrowLeft className="w-4 h-4" /> {t("backToInterview")}
      </button>

      {/* ── Hero: Decision + Score ──────────────────────────────────────────── */}
      <Card>
        <div className={cn("px-6 py-5 border-b", dcfg.border, dcfg.bg)}>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">

            <div className="flex items-center gap-3 flex-1">
              <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-sm", dcfg.badge)}>
                <DecisionIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{t("hiringDecision")}</p>
                <p className={cn("text-2xl font-bold", dcfg.text)}>{t(dcfg.labelKey)}</p>
              </div>
            </div>

            <div className="flex items-center gap-5">
              <RingGauge
                value={overall_score}
                max={100}
                size={88}
                color={overall_score >= 70 ? "#22c55e" : overall_score >= 50 ? "#f59e0b" : "#ef4444"}
                label={t("overallScore")}
                sub="/100"
              />
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2 text-slate-600">
                  <Users className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs">{state.candidateName || t("candidate")}</span>
                </div>
                {state.candidateEmail && (
                  <div className="flex items-center gap-2 text-slate-500">
                    <span className="text-xs">{state.candidateEmail}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-slate-500">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs">
                    {generated_at ? format(new Date(generated_at), "MMM d, yyyy · HH:mm") : "—"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-slate-500">
                  <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs">{qa_pairs_count} {t("questionsEvaluated")}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </Card>

      {/* ── HR Summary ─────────────────────────────────────────────────────── */}
      {hr_summary && (
        <Card>
          <CardHeader icon={Award} title={t("hrSummary")} sub={t("aiGeneratedAssessment")} iconColor="bg-violet-500" />
          <div className="px-5 py-4 flex gap-3">
            <Quote className="w-5 h-5 text-violet-300 shrink-0 mt-0.5" />
            <p className="text-sm text-slate-700 leading-relaxed">{hr_summary}</p>
          </div>
        </Card>
      )}

      {/* ── Row 1: Text + Engagement ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Text Analysis */}
        <Card>
          <CardHeader icon={Brain} title={t("textAnalysis")} sub={t("clarityRelevanceConfidence")} iconColor="bg-indigo-500" />
          <div className="px-5 py-5 space-y-5">
            <div className="flex items-center justify-around">
              <RingGauge value={text_metrics.clarity_score ?? 0} max={10} size={88} color="#6366f1" label={t("clarityLabel")} sub="/10" />
              <RingGauge value={text_metrics.relevance_score ?? 0} max={10} size={88} color="#8b5cf6" label={t("relevanceLabel")} sub="/10" />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">{t("languageConfidence")}</span>
              <span className={cn(
                "text-[11px] font-semibold px-2.5 py-1 rounded-full border",
                text_metrics.confidence_level === "high"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : text_metrics.confidence_level === "medium"
                  ? "bg-amber-50 text-amber-700 border-amber-200"
                  : "bg-slate-100 text-slate-500 border-slate-200"
              )}>
                {t(CONFIDENCE_KEY_MAP[text_metrics.confidence_level] || "confidenceUnknown")}
              </span>
            </div>

            {relevanceData.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-600 mb-2">{t("perQuestionRelevance")}</p>
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={relevanceData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f8fafc" }} />
                    <Bar dataKey="score" name={t("relevanceLabel")} fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </Card>

        {/* Engagement */}
        <Card>
          <CardHeader icon={Eye} title={t("engagementLabel")} sub={t("faceFocusQuality")} iconColor="bg-emerald-500" />
          <div className="px-5 py-5 space-y-5">
            <div className="flex items-center justify-around">
              <RingGauge value={engagement_metrics.engagement_rate ?? 0} max={100} size={88} color="#22c55e" label={t("engagementRate")} sub="%" />
              <RingGauge value={engagement_metrics.face_detection_rate ?? 0} max={100} size={88} color="#0ea5e9" label={t("faceDetected")} sub="%" />
            </div>

            <div className="space-y-3">
              <MetricBar label={t("emotionStability")} value={engagement_metrics.emotion_stability ?? 0} color="bg-emerald-400" />
              <MetricBar label={t("detectionQuality")} value={engagement_metrics.detection_quality ?? 0} color="bg-sky-400" />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">{t("focusQuality")}</span>
              <span className={cn(
                "text-[11px] font-semibold px-2.5 py-1 rounded-full border capitalize",
                FOCUS_CFG[engagement_metrics.focus_quality] ?? FOCUS_CFG.low
              )}>
                {t(FOCUS_KEY_MAP[engagement_metrics.focus_quality] || "focusLow")}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* ── Soft Skills ────────────────────────────────────────────────────── */}
      {detected_skills.length > 0 && (
        <Card>
          <CardHeader
            icon={Zap}
            title={t("detectedSoftSkillsTitle")}
            sub={`${detected_skills.length} ${t("competenciesIdentified")}`}
            iconColor="bg-violet-500"
          />
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {detected_skills.map((skill, i) => {
              const cfg = STRENGTH_CFG[skill.strength] || STRENGTH_CFG.moderate;
              const label = skill.display_name || skill.name.replace(/_/g, " ");
              return (
                <div key={i} className="rounded-xl border border-slate-200 p-3.5 space-y-2 hover:shadow-sm transition-shadow">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-800 capitalize">{label}</p>
                    <span className={cn(
                      "text-[10px] font-semibold px-2 py-0.5 rounded-full border capitalize shrink-0",
                      cfg.color
                    )}>
                      {t(STRENGTH_KEY_MAP[skill.strength] || "strengthModerate")}
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className={cn("h-full rounded-full", cfg.bar, cfg.w)} />
                  </div>
                  {skill.quote && (
                    <p className="text-[11px] text-slate-500 italic leading-relaxed border-l-2 border-slate-200 pl-2">
                      "{skill.quote}"
                    </p>
                  )}
                  {skill.description && (
                    <p className="text-[11px] text-slate-400 leading-relaxed">{skill.description}</p>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* ── Emotion Timeline ───────────────────────────────────────────────── */}
      {timelineData.length > 1 && (
        <Card>
          <CardHeader
            icon={Activity}
            title={t("emotionTimelineTitle")}
            sub={`${rawTimeline.length} ${t("framesAnalysed")} · ${t("trackingEmotions")}`}
            iconColor="bg-rose-500"
          />

          {/* Dominant emotion */}
          <div className="px-5 pt-4 pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-xl px-3 py-2 w-fit">
              <span className="text-2xl">{EMOTION_EMOJI[dominantEmotion] ?? "😐"}</span>
              <div>
                <p className="text-[10px] text-slate-400">{t("dominantEmotion")}</p>
                <p className="text-xs font-semibold text-slate-800">{tEmotion(dominantEmotion)}</p>
              </div>
            </div>
          </div>
          <div className="px-5 py-5">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={timelineData} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false} tickLine={false}
                  tickFormatter={(v) => `${v}s`}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false} tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip content={(props) => <ChartTooltip {...props} tEmotion={tEmotion} />} />
                <Legend
                  iconSize={8}
                  iconType="circle"
                  formatter={(v) => <span style={{ fontSize: 11, color: "#64748b" }}>{tEmotion(v)}</span>}
                />
                {timelineKeys.map((key) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    name={key}
                    stroke={EMOTION_COLORS[key] ?? "#94a3b8"}
                    strokeWidth={1.5}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

    </div>
  );
}

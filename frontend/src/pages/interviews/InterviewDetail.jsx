// src/pages/interviews/InterviewDetail.jsx
import { useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  useInterview, useCreateInterview, useUpdateInterview,
  useCreateQuestion, useUpdateQuestion, useDeleteQuestion,
  useGenerateQuestions, useEnhanceQuestion,
  useGenerateRubric, useEnhanceRubric,
  useInterviewCandidates, useAssignCandidate,
} from "../../hooks/useInterviews";
import { useJobs } from "../../hooks/useJobs";
import { useSoftskillsBank } from "../../hooks/useSoftskills";
import { Button }   from "@/components/ui/button";
import { Input }    from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label }    from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft, Plus, Pencil, Trash2,
  Check, X, Mic, GripVertical,
  Code2, Users, Briefcase, Layers,
  ChevronDown, Sparkles, Loader2,
  RefreshCw, AlertCircle, BookOpen, Wand2,
  Copy, Link2, UserRound, FileText,
} from "lucide-react";
import { cn }    from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { toast } from "sonner";
import { format } from "date-fns";

const TYPES = [
  { value: "behavioral", labelKey: "typeBehavioral", icon: Users,     color: "border-blue-300   bg-blue-50   text-blue-700",    ring: "ring-blue-300"    },
  { value: "technical",  labelKey: "typeTechnical",  icon: Code2,     color: "border-violet-300 bg-violet-50 text-violet-700",  ring: "ring-violet-300"  },
  { value: "hr",         labelKey: "typeHr",         icon: Briefcase, color: "border-emerald-300 bg-emerald-50 text-emerald-700", ring: "ring-emerald-300" },
  { value: "mixed",      labelKey: "typeMixed",      icon: Layers,    color: "border-amber-300  bg-amber-50  text-amber-700",   ring: "ring-amber-300"   },
];
const TYPE_MAP = Object.fromEntries(TYPES.map((t) => [t.value, t]));

// ── Job selector ─────────────────────────────────────────────────────────────
function JobSelector({ value, onChange, error }) {
  const { data: jobs = [], isLoading } = useJobs();
  const [open, setOpen] = useState(false);
  const selected = jobs.find((j) => j.id === value);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "w-full flex items-center justify-between gap-2 h-9 px-3 rounded-md border bg-white text-sm transition-colors",
          "hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-900/10",
          error ? "border-red-300" : "border-slate-200",
          !selected && "text-slate-400"
        )}
      >
        {isLoading ? (
          <span className="text-slate-400">Loading jobs…</span>
        ) : selected ? (
          <span className="truncate text-slate-900">
            <span className="font-medium">{selected.title}</span>
            <span className="text-slate-400 ml-1.5">· {selected.company}</span>
          </span>
        ) : (
          <span>Select a job…</span>
        )}
        <ChevronDown className={cn("w-4 h-4 text-slate-400 shrink-0 transition-transform", open && "rotate-180")} />
      </button>

      {open && !isLoading && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden">
          <div className="max-h-52 overflow-y-auto">
            {jobs.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-6">No jobs found.</p>
            ) : (
              jobs.map((job) => (
                <button key={job.id} type="button"
                  onClick={() => { onChange(job.id); setOpen(false); }}
                  className={cn(
                    "w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-slate-50 transition-colors",
                    value === job.id && "bg-slate-50"
                  )}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">{job.title}</p>
                    <p className="text-xs text-slate-400 truncate">{job.company}</p>
                  </div>
                  {value === job.id && <Check className="w-4 h-4 text-slate-900 shrink-0 mt-0.5" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Create Interview Form ────────────────────────────────────────────────────
function CreateInterviewForm({ jobId, jobTitle }) {
  const navigate        = useNavigate();
  const createInterview = useCreateInterview();
  const { t, lang }     = useI18n();

  const [form, setForm] = useState({
    job_id:   jobId || "",
    type:     "behavioral",
    title:    jobTitle ? `${jobTitle} Interview` : "",
    notes:    "",
    language: lang,
  });
  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (!form.job_id.trim()) e.job_id = "Please select a job";
    if (!form.title.trim())  e.title  = "Title is required";
    return e;
  };

  const handleSubmit = async () => {
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    try {
      const result = await createInterview.mutateAsync(form);
      toast.success("Interview created!");
      navigate(`/interviews/${result.id}`, { replace: true });
    } catch (err) {
      if (err?.response?.status === 409) toast.error("This job already has an interview.");
      else toast.error(err?.response?.data?.detail || "Failed to create interview");
    }
  };

  return (
    <div className="max-w-xl mx-auto">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-slate-700">
            {t("interviewTitle")} <span className="text-red-400">*</span>
          </Label>
          <Input placeholder="e.g. Frontend Engineer – Technical Round"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            className={cn("h-9 text-sm", errors.title && "border-red-300")}
          />
          {errors.title && <p className="text-xs text-red-500">{errors.title}</p>}
        </div>

        {!jobId && (
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-700">
              Job <span className="text-red-400">*</span>
            </Label>
            <JobSelector value={form.job_id}
              onChange={(id) => setForm((f) => ({ ...f, job_id: id }))}
              error={errors.job_id}
            />
            {errors.job_id && <p className="text-xs text-red-500">{errors.job_id}</p>}
          </div>
        )}

        <div className="space-y-2">
          <Label className="text-xs font-medium text-slate-700">{t("interviewType")}</Label>
          <div className="grid grid-cols-2 gap-2">
            {TYPES.map(({ value, labelKey, icon: Icon, color, ring }) => (
              <button key={value} type="button"
                onClick={() => setForm((f) => ({ ...f, type: value }))}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-sm font-medium transition-all",
                  form.type === value
                    ? cn(color, "ring-2 ring-offset-1", ring)
                    : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
                )}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {t(labelKey)}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-slate-700">{t("interviewLanguage")}</Label>
          <div className="flex gap-2">
            {["en", "fr"].map((lng) => (
              <button key={lng} type="button"
                onClick={() => setForm((f) => ({ ...f, language: lng }))}
                className={cn(
                  "flex-1 h-9 rounded-lg border text-sm font-medium transition-all",
                  form.language === lng
                    ? "bg-slate-900 text-white border-slate-900"
                    : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
                )}
              >
                {lng === "en" ? t("langEnglish") : t("langFrench")}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-slate-700">{t("notesOptional")}</Label>
          <Textarea placeholder="Any notes about this interview round…"
            rows={3} value={form.notes}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            className="text-sm resize-none"
          />
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={() => navigate(-1)}>{t("cancel")}</Button>
          <Button size="sm" onClick={handleSubmit} disabled={createInterview.isPending}
            className="bg-slate-900 hover:bg-slate-700 text-white min-w-32.5">
            {createInterview.isPending ? t("creating") : t("createInterview")}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── AI Generate Questions Panel ──────────────────────────────────────────────
function GenerateQuestionsPanel({ interview, job, onClose }) {
  const [count, setCount]     = useState(10);
  const generateQ             = useGenerateQuestions(interview.id);
  const createQ               = useCreateQuestion(interview.id);
  const [preview, setPreview] = useState(null);

  const handleGenerate = async () => {
    if (!job) { toast.error("Job data not available"); return; }
    try {
      const questions = await generateQ.mutateAsync({
        title:           job.title,
        company:         job.company,
        interview_type:  interview.type,
        seniority_level: job.seniority_level,
        description:     job.description  || "",
        requirements:    job.requirements || "",
        count,
        language:        interview.language || "en",
      });
      setPreview(questions);
    } catch {
      toast.error("Failed to generate questions");
    }
  };

  const handleSaveAll = async () => {
    if (!preview?.length) return;
    try {
      await Promise.all(
        preview.map((q, i) => createQ.mutateAsync({ question: q, order_index: i }))
      );
      toast.success(`${preview.length} questions added!`);
      onClose();
    } catch {
      toast.error("Failed to save questions");
    }
  };

  return (
    <div className="border-t border-slate-100 bg-linear-to-b from-slate-50/80 to-white">

      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-indigo-100 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          </div>
          <span className="text-sm font-semibold text-slate-900">Generate with AI</span>
          <span className="text-xs text-slate-400 ml-1">
            · {interview.type} · {job?.seniority_level ?? "—"}
          </span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-slate-400" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      <div className="px-5 py-4 space-y-4">
        {job && (
          <div className="flex flex-wrap gap-1.5">
            {[
              { label: job.title,           icon: Briefcase },
              { label: job.company,         icon: null       },
              { label: job.seniority_level, icon: null       },
              { label: interview.type,      icon: null       },
            ].map(({ label, icon: Icon }, i) => (
              <span key={i}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-xs text-slate-600 capitalize">
                {Icon && <Icon className="w-3 h-3 text-slate-400" />}
                {label}
              </span>
            ))}
          </div>
        )}

        {!job && (
          <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            Job details not loaded — questions will be generic.
          </div>
        )}

        <div className="flex items-center gap-3">
          <Label className="text-xs text-slate-600 shrink-0">Number of questions</Label>
          <div className="flex gap-1.5">
            {[5, 8, 10, 15, 20].map((n) => (
              <button key={n} onClick={() => setCount(n)}
                className={cn(
                  "w-9 h-7 rounded-lg text-xs font-medium border transition-all",
                  count === n
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
                )}>
                {n}
              </button>
            ))}
          </div>
        </div>

        {!preview && (
          <Button onClick={handleGenerate} disabled={generateQ.isPending}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white gap-2 h-9">
            {generateQ.isPending
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating {count} questions…</>
              : <><Sparkles className="w-4 h-4" /> Generate {count} Questions</>
            }
          </Button>
        )}

        {preview && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-slate-700">Preview — {preview.length} questions</p>
              <button onClick={() => setPreview(null)}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors">
                <RefreshCw className="w-3 h-3" />
                Regenerate
              </button>
            </div>

            <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
              {preview.map((q, i) => (
                <div key={i} className="flex items-start gap-3 bg-white rounded-xl border border-slate-100 px-3.5 py-3">
                  <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <p className="text-sm text-slate-700 leading-relaxed">{q}</p>
                </div>
              ))}
            </div>

            <div className="flex gap-2 pt-1">
              <Button variant="outline" size="sm" className="flex-1 gap-1.5 text-xs"
                onClick={() => setPreview(null)} disabled={createQ.isPending}>
                <RefreshCw className="w-3.5 h-3.5" />
                Regenerate
              </Button>
              <Button size="sm"
                className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5 text-xs"
                onClick={handleSaveAll} disabled={createQ.isPending}>
                {createQ.isPending
                  ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving…</>
                  : <><Check className="w-3.5 h-3.5" /> Add All to Interview</>
                }
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Single question row ──────────────────────────────────────────────────────
function QuestionRow({ question, interview, job, interviewId, index }) {
  const [editing,       setEditing]       = useState(false);
  const [text,          setText]          = useState(question.question);
  const [enhancing,     setEnhancing]     = useState(false);
  const [showDetails,   setShowDetails]   = useState(false);
  const [rubric,        setRubric]        = useState(question.rubric || "");
  const [editingRubric, setEditingRubric] = useState(false);

  const updateQ        = useUpdateQuestion(interviewId);
  const deleteQ        = useDeleteQuestion(interviewId);
  const enhanceQ       = useEnhanceQuestion(interviewId);
  const generateRubric = useGenerateRubric(interviewId);
  const enhanceRubric  = useEnhanceRubric(interviewId);

  const roleContext = {
    title:           job?.title           || "",
    interview_type:  interview.type,
    seniority_level: job?.seniority_level || "",
    language:        interview.language   || "en",
  };

  const save = async () => {
    if (!text.trim()) return;
    try {
      await updateQ.mutateAsync({ questionId: question.id, data: { question: text } });
      setEditing(false);
      toast.success("Question updated");
    } catch { toast.error("Failed to update question"); }
  };

  const cancel = () => { setText(question.question); setEditing(false); };

  const remove = async () => {
    try {
      await deleteQ.mutateAsync(question.id);
      toast.success("Question deleted");
    } catch { toast.error("Failed to delete question"); }
  };

  const handleEnhance = async () => {
    if (!job) { toast.error("Job data not available"); return; }
    setEnhancing(true);
    try {
      const improved = await enhanceQ.mutateAsync({
        questionId: question.id,
        payload: { ...roleContext, question: question.question },
      });
      setText(improved);
      setEditing(true);
      toast.success("Question enhanced — review and save");
    } catch { toast.error("Failed to enhance question"); }
    finally { setEnhancing(false); }
  };

  const handleGenerateRubric = async () => {
    if (!job) { toast.error("Job data not available"); return; }
    try {
      const result = await generateRubric.mutateAsync({
        questionId: question.id,
        payload: { ...roleContext, question: text || question.question },
      });
      setRubric(result);
      setEditingRubric(true);
      toast.success("Rubric generated — review and save");
    } catch { toast.error("Failed to generate rubric"); }
  };

  const handleEnhanceRubric = async () => {
    if (!rubric.trim()) { toast.error("No rubric to enhance"); return; }
    try {
      const result = await enhanceRubric.mutateAsync({
        questionId: question.id,
        payload: { ...roleContext, question: text || question.question, rubric },
      });
      setRubric(result);
      setEditingRubric(true);
      toast.success("Rubric enhanced — review and save");
    } catch { toast.error("Failed to enhance rubric"); }
  };

  const saveRubric = async () => {
    try {
      await updateQ.mutateAsync({ questionId: question.id, data: { rubric } });
      setEditingRubric(false);
      toast.success("Rubric saved");
    } catch { toast.error("Failed to save rubric"); }
  };

  return (
    <div className="border-b border-slate-100 last:border-0">

      <div className="group flex items-start gap-3 px-5 py-4 hover:bg-slate-50/50 transition-colors">
        <div className="flex items-center gap-2 shrink-0 mt-0.5">
          <GripVertical className="w-4 h-4 text-slate-300" />
          <span className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-xs font-semibold text-slate-500 shrink-0">
            {index + 1}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          {editing ? (
            <div className="space-y-2">
              <Textarea value={text} onChange={(e) => setText(e.target.value)}
                rows={3} autoFocus className="text-sm resize-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save();
                  if (e.key === "Escape") cancel();
                }}
              />
              <div className="flex gap-1.5">
                <Button size="sm" onClick={save} disabled={updateQ.isPending}
                  className="h-7 text-xs bg-slate-900 hover:bg-slate-700 text-white gap-1">
                  <Check className="w-3 h-3" />
                  {updateQ.isPending ? "Saving…" : "Save"}
                </Button>
                <Button size="sm" variant="outline" onClick={cancel} className="h-7 text-xs gap-1">
                  <X className="w-3 h-3" />Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-slate-700 leading-relaxed">{question.question}</p>
              {rubric && !showDetails && (
                <p className="text-[11px] text-slate-400 truncate">
                  <span className="font-medium text-slate-500">Rubric: </span>
                  {rubric.split("\n")[0]}…
                </p>
              )}
            </div>
          )}
        </div>

        {!editing && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            <Button variant="ghost" size="icon"
              className={cn("h-7 w-7 hover:bg-slate-100", showDetails ? "text-indigo-600 bg-indigo-50" : "text-slate-400")}
              onClick={() => setShowDetails((v) => !v)}
              title="Rubric">
              <BookOpen className="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="icon"
              className="h-7 w-7 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50"
              onClick={handleEnhance} disabled={enhancing} title="Enhance with AI">
              {enhancing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            </Button>
            <Button variant="ghost" size="icon"
              className="h-7 w-7 text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              onClick={() => setEditing(true)}>
              <Pencil className="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="icon"
              className="h-7 w-7 text-slate-400 hover:text-red-500 hover:bg-red-50"
              onClick={remove} disabled={deleteQ.isPending}>
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        )}
      </div>

      {showDetails && (
        <div className="mx-5 mb-4 rounded-xl border border-slate-200 bg-slate-50/60 overflow-hidden">
          <div className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                Scoring Rubric
              </span>
              <div className="flex items-center gap-1">
                {rubric && (
                  <Button variant="ghost" size="sm"
                    className="h-6 px-2 text-[10px] text-slate-500 hover:text-indigo-600 gap-1"
                    onClick={handleEnhanceRubric} disabled={enhanceRubric.isPending}>
                    {enhanceRubric.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                    Enhance
                  </Button>
                )}
                <Button variant="ghost" size="sm"
                  className="h-6 px-2 text-[10px] text-indigo-600 hover:text-indigo-700 gap-1"
                  onClick={handleGenerateRubric} disabled={generateRubric.isPending}>
                  {generateRubric.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                  {rubric ? "Regenerate" : "Generate"}
                </Button>
              </div>
            </div>

            {editingRubric ? (
              <div className="space-y-2">
                <Textarea value={rubric} onChange={(e) => setRubric(e.target.value)}
                  rows={4} className="text-xs font-mono resize-none bg-white" autoFocus />
                <div className="flex gap-1.5">
                  <Button size="sm" onClick={saveRubric} disabled={updateQ.isPending}
                    className="h-6 text-[10px] bg-slate-900 text-white gap-1">
                    <Check className="w-3 h-3" />
                    {updateQ.isPending ? "Saving…" : "Save rubric"}
                  </Button>
                  <Button size="sm" variant="outline" className="h-6 text-[10px]"
                    onClick={() => { setRubric(question.rubric || ""); setEditingRubric(false); }}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : rubric ? (
              <div className="space-y-1">
                {rubric.split("\n").filter(Boolean).map((line, i) => (
                  <p key={i} className="text-xs text-slate-600 leading-relaxed">
                    <span className="font-medium text-slate-700">{line.split(":")[0]}:</span>
                    {line.split(":").slice(1).join(":")}
                  </p>
                ))}
                <button onClick={() => setEditingRubric(true)}
                  className="text-[10px] text-slate-400 hover:text-slate-600 mt-1">
                  Edit rubric
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-slate-400 italic">
                  No rubric yet — generate one with AI or write manually.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 text-[10px]"
                  onClick={() => setEditingRubric(true)}
                >
                  Write rubric
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Add question inline form ─────────────────────────────────────────────────
function AddQuestionForm({ interviewId, onDone }) {
  const [text, setText] = useState("");
  const [rubric, setRubric] = useState("");
  const createQ         = useCreateQuestion(interviewId);

  const handleAdd = async () => {
    if (!text.trim()) return;
    try {
      await createQ.mutateAsync({
        question: text,
        order_index: 0,
        rubric: rubric.trim() || null,
      });
      setText("");
      setRubric("");
      toast.success("Question added");
      onDone?.();
    } catch { toast.error("Failed to add question"); }
  };

  return (
    <div className="px-5 py-4 bg-slate-50/80 border-t border-slate-100 space-y-2">
      <Textarea placeholder="Type your question… (Ctrl+Enter to save)"
        rows={3} value={text} onChange={(e) => setText(e.target.value)}
        className="text-sm resize-none bg-white" autoFocus
        onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAdd(); }}
      />
      <Textarea
        placeholder="Optional rubric (you can also generate/enhance later with AI)"
        rows={3}
        value={rubric}
        onChange={(e) => setRubric(e.target.value)}
        className="text-xs resize-none bg-white"
      />
      <div className="flex justify-end gap-1.5">
        <Button variant="outline" size="sm" className="h-7 text-xs"
          onClick={() => { setText(""); setRubric(""); onDone?.(); }}>
          Cancel
        </Button>
        <Button size="sm" onClick={handleAdd}
          disabled={createQ.isPending || !text.trim()}
          className="h-7 text-xs bg-slate-900 hover:bg-slate-700 text-white gap-1">
          <Plus className="w-3 h-3" />
          {createQ.isPending ? "Adding…" : "Add Question"}
        </Button>
      </div>
    </div>
  );
}


function CandidateAssignmentsPanel({ interviewId, disabled }) {
  const { data: candidates = [], isLoading } = useInterviewCandidates(interviewId);
  const assignCandidate = useAssignCandidate(interviewId);
  const { t, tv } = useI18n();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const handleAssign = async () => {
    if (!name.trim() || !email.trim()) {
      toast.error("Candidate name and email are required.");
      return;
    }
    try {
      await assignCandidate.mutateAsync({ name: name.trim(), email: email.trim() });
      setName("");
      setEmail("");
      toast.success("Candidate assigned successfully.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Failed to assign candidate.");
    }
  };

  const copyLink = async (token) => {
    const link = `${window.location.origin}/candidate/${token}`;
    try {
      await navigator.clipboard.writeText(link);
      toast.success("Candidate link copied.");
    } catch {
      toast.error("Failed to copy candidate link.");
    }
  };

  const openReport = (candidate) => {
    navigate(
      `/interviews/${interviewId}/candidates/${candidate.id}/report`,
      { state: { candidateName: candidate.name, candidateEmail: candidate.email } }
    );
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="text-sm font-semibold text-slate-900">{t("candidatesSubmissions")}</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Assign candidates, collect their video submissions, and review processed reports.
        </p>
      </div>

      <div className="px-5 py-4 border-b border-slate-100 space-y-3 bg-slate-50/60">
        {disabled && (
          <p className="text-[11px] text-amber-600">
            Add interview questions first before assigning candidates.
          </p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Candidate full name"
            disabled={disabled || assignCandidate.isPending}
            className="h-9 text-sm"
          />
          <Input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="candidate@email.com"
            disabled={disabled || assignCandidate.isPending}
            className="h-9 text-sm"
          />
        </div>
        <Button
          size="sm"
          onClick={handleAssign}
          disabled={disabled || assignCandidate.isPending}
          className="bg-slate-900 hover:bg-slate-700 text-white h-8 text-xs gap-1.5"
        >
          <UserRound className="w-3.5 h-3.5" />
          {assignCandidate.isPending ? "Assigning…" : "Assign Candidate"}
        </Button>
      </div>

      <div className="p-5 space-y-3">
        {isLoading ? (
          <p className="text-xs text-slate-400">Loading candidates…</p>
        ) : candidates.length === 0 ? (
          <p className="text-xs text-slate-400">No candidates assigned yet.</p>
        ) : (
          candidates.map((candidate) => {
            const report = candidate.analysis_payload || null;
            return (
              <div key={candidate.id} className="rounded-xl border border-slate-200 p-3 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{candidate.name}</p>
                    <p className="text-xs text-slate-500">{candidate.email}</p>
                  </div>
                  <span className={cn(
                    "text-[10px] px-2 py-1 rounded-full border font-semibold uppercase tracking-wide",
                    candidate.status === "processed" && "border-emerald-200 bg-emerald-50 text-emerald-700",
                    candidate.status === "submitted" && "border-blue-200 bg-blue-50 text-blue-700",
                    candidate.status === "failed" && "border-red-200 bg-red-50 text-red-700",
                    candidate.status === "assigned" && "border-slate-200 bg-slate-50 text-slate-600"
                  )}>
                    {tv(candidate.status)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-[11px] gap-1"
                    onClick={() => copyLink(candidate.access_token)}
                  >
                    <Copy className="w-3 h-3" />
                    {t("copyCandidateLink")}
                  </Button>
                  <a
                    href={`${window.location.origin}/candidate/${candidate.access_token}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-indigo-600 hover:text-indigo-700"
                  >
                    <Link2 className="w-3 h-3" />
                    {t("openLink")}
                  </a>
                  {candidate.status === "processed" && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 text-[11px] gap-1"
                      onClick={() => openReport(candidate)}
                    >
                      <FileText className="w-3 h-3" />
                      {t("openFullReport")}
                    </Button>
                  )}
                </div>

                {report && (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                    <div className="flex items-center gap-3 text-xs text-slate-600">
                        <span className="font-semibold text-slate-800">{t("decision")}: {tv(report.decision || "REVIEW")}</span>
                      <span>Score: {report.overall_score ?? 0}</span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {report.hr_summary || "Report generated successfully."}
                    </p>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

    </div>
  );
}

// ── Main export ──────────────────────────────────────────────────────────────
export default function InterviewDetail() {
  const { id }         = useParams();
  const [searchParams] = useSearchParams();
  const navigate       = useNavigate();

  const [showAdd,      setShowAdd]      = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleText,    setTitleText]    = useState("");

  const isNew    = id === "new";
  const jobId    = searchParams.get("job_id");
  const jobTitle = searchParams.get("job_title");

  const { t, lang } = useI18n();
  const { data: interview, isLoading, isError } = useInterview(isNew ? null : id);
  const { data: jobs = [] } = useJobs();
  const { data: bankSkills = [] } = useSoftskillsBank({ active: true });
  const updateInterview = useUpdateInterview();

  const job = interview ? jobs.find((j) => j.id === interview.job_id) : null;

  const availableSkills = useMemo(() => {
    const byKey = new Map();
    for (const item of bankSkills || []) {
      if (!item?.key) continue;
      const existing = byKey.get(item.key);
      if (!existing || item.language === "en") {
        byKey.set(item.key, item);
      }
    }
    return Array.from(byKey.values()).sort((a, b) => a.key.localeCompare(b.key));
  }, [bankSkills]);

  const selectedTargetSkills = interview?.target_softskills || [];
  const hasQuestions = (interview?.questions?.length || 0) > 0;

  const toggleInterviewTargetSkill = async (key) => {
    if (!hasQuestions) {
      toast.error("Add interview questions first, then select target soft skills.");
      return;
    }
    const hasSkill = selectedTargetSkills.includes(key);
    const updatedSkills = hasSkill
      ? selectedTargetSkills.filter((skill) => skill !== key)
      : [...selectedTargetSkills, key];

    try {
      await updateInterview.mutateAsync({ id, data: { target_softskills: updatedSkills } });
      toast.success("Interview target soft skills updated");
    } catch {
      toast.error("Failed to update interview target soft skills");
    }
  };

  const saveTitle = async () => {
    if (!titleText.trim()) return;
    try {
      await updateInterview.mutateAsync({ id, data: { title: titleText } });
      setEditingTitle(false);
      toast.success("Title updated");
    } catch { toast.error("Failed to update title"); }
  };

  if (isNew) {
    return (
      <div className="space-y-5 max-w-4xl mx-auto">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}
            className="text-slate-500 hover:text-slate-900 gap-1.5 -ml-2">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900">New Interview</h1>
            {jobTitle && (
              <p className="text-sm text-slate-400 mt-0.5">for {decodeURIComponent(jobTitle)}</p>
            )}
          </div>
        </div>
        <CreateInterviewForm jobId={jobId} jobTitle={jobTitle ? decodeURIComponent(jobTitle) : ""} />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-5 max-w-4xl mx-auto">
        <Skeleton className="h-8 w-48 rounded" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (isError || !interview) {
    return (
      <div className="text-center py-16 max-w-4xl mx-auto">
        <p className="text-slate-500 mb-3">Interview not found.</p>
        <Button variant="outline" size="sm" onClick={() => navigate("/interviews")}>
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Interviews
        </Button>
      </div>
    );
  }

  const typeConfig = TYPE_MAP[interview.type] ?? TYPES[0];
  const TypeIcon   = typeConfig.icon;

  return (
    <div className="space-y-5 max-w-4xl mx-auto">

      <Button variant="ghost" size="sm" onClick={() => navigate("/interviews")}
        className="text-slate-500 hover:text-slate-900 gap-1.5 -ml-2">
        <ArrowLeft className="w-4 h-4" />
        All Interviews
      </Button>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-start gap-4">
          <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border", typeConfig.color)}>
            <TypeIcon className="w-6 h-6" />
          </div>

          <div className="flex-1 min-w-0">
            {editingTitle ? (
              <div className="flex items-center gap-2">
                <Input value={titleText} onChange={(e) => setTitleText(e.target.value)}
                  className="h-8 text-sm font-semibold" autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter")  saveTitle();
                    if (e.key === "Escape") setEditingTitle(false);
                  }}
                />
                <Button size="icon" variant="ghost" className="h-8 w-8 text-emerald-600 hover:bg-emerald-50" onClick={saveTitle}>
                  <Check className="w-4 h-4" />
                </Button>
                <Button size="icon" variant="ghost" className="h-8 w-8 text-slate-400" onClick={() => setEditingTitle(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2 group/title">
                <h1 className="text-lg font-bold text-slate-900 leading-tight">{interview.title}</h1>
                <button onClick={() => { setTitleText(interview.title); setEditingTitle(true); }}
                  className="opacity-0 group-hover/title:opacity-100 transition-opacity p-1 rounded hover:bg-slate-100">
                  <Pencil className="w-3.5 h-3.5 text-slate-400" />
                </button>
              </div>
            )}

            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <span className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border capitalize",
                typeConfig.color
              )}>
                <TypeIcon className="w-3 h-3" />
                {t(typeConfig.labelKey)}
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border border-slate-200 bg-slate-50 text-slate-600 uppercase">
                {interview.language || "en"}
              </span>
              {job && (
                <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                  <Briefcase className="w-3 h-3 text-slate-400" />
                  {job.title} · {job.company}
                </span>
              )}
              <span className="text-xs text-slate-400">
                Created {format(new Date(interview.created_at), "MMMM d, yyyy")}
              </span>
              <span className="text-xs text-slate-400 font-medium">
                {interview.questions?.length ?? 0} question{interview.questions?.length !== 1 ? "s" : ""}
              </span>
            </div>

            {interview.notes && (
              <p className="text-sm text-slate-500 mt-2 leading-relaxed">{interview.notes}</p>
            )}

            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/70 p-3 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-slate-700">Interview Target Soft Skills</p>
                <span className="text-[11px] text-slate-500">
                  {selectedTargetSkills.length} selected
                </span>
              </div>

              {!hasQuestions && (
                <p className="text-[11px] text-amber-600">
                  Create questions (and rubric if needed) first, then select interview target soft skills.
                </p>
              )}

              {availableSkills.length === 0 ? (
                <p className="text-xs text-slate-400">No active soft skills found in bank.</p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {availableSkills.map((skill) => {
                    const selected = selectedTargetSkills.includes(skill.key);
                    return (
                      <button
                        key={skill.id}
                        type="button"
                        onClick={() => toggleInterviewTargetSkill(skill.key)}
                        className={cn(
                          "rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors",
                          !hasQuestions && "opacity-50 cursor-not-allowed",
                          selected
                            ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                            : "border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
                        )}
                        disabled={!hasQuestions}
                        title={skill.description}
                      >
                        {skill.display_name || skill.key}
                      </button>
                    );
                  })}
                </div>
              )}

              <p className="text-[10px] text-slate-400">
                These skills will be prioritized during transcript soft-skill verification.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">

        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Questions</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {interview.questions?.length
                ? `${interview.questions.length} question${interview.questions.length !== 1 ? "s" : ""}`
                : "No questions yet"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline"
              onClick={() => { setShowGenerate((v) => !v); setShowAdd(false); }}
              className={cn(
                "gap-1.5 h-8 px-3 text-xs border transition-all",
                showGenerate
                  ? "bg-indigo-50 border-indigo-300 text-indigo-700 hover:bg-indigo-100"
                  : "text-slate-600 hover:text-indigo-600 hover:border-indigo-300 hover:bg-indigo-50"
              )}>
              <Sparkles className="w-3.5 h-3.5" />
              Generate with AI
            </Button>
            {!showAdd && (
              <Button size="sm"
                onClick={() => { setShowAdd(true); setShowGenerate(false); }}
                className="bg-slate-900 hover:bg-slate-700 text-white gap-1.5 h-8 px-3 text-xs">
                <Plus className="w-3.5 h-3.5" />
                Add
              </Button>
            )}
          </div>
        </div>

        {showGenerate && (
          <GenerateQuestionsPanel
            interview={interview}
            job={job}
            onClose={() => setShowGenerate(false)}
          />
        )}

        {!interview.questions?.length && !showAdd && !showGenerate && (
          <div className="py-14 text-center">
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
              <Mic className="w-5 h-5 text-slate-400" />
            </div>
            <p className="text-sm font-medium text-slate-700">No questions yet</p>
            <p className="text-xs text-slate-400 mt-1 mb-5">Add manually or let AI generate them for you</p>
            <div className="flex items-center justify-center gap-2">
              <Button size="sm" variant="outline"
                onClick={() => setShowGenerate(true)}
                className="gap-1.5 text-xs text-indigo-600 border-indigo-200 hover:bg-indigo-50">
                <Sparkles className="w-3.5 h-3.5" />
                Generate with AI
              </Button>
              <Button size="sm"
                onClick={() => setShowAdd(true)}
                className="bg-slate-900 hover:bg-slate-700 text-white gap-1.5 text-xs">
                <Plus className="w-3.5 h-3.5" />
                Add Manually
              </Button>
            </div>
          </div>
        )}

        {interview.questions?.map((q, i) => (
          <QuestionRow
            key={q.id}
            question={q}
            interview={interview}
            job={job}
            interviewId={id}
            index={i}
          />
        ))}

        {showAdd && (
          <AddQuestionForm interviewId={id} onDone={() => setShowAdd(false)} />
        )}
      </div>

      <CandidateAssignmentsPanel interviewId={id} disabled={!hasQuestions} />
    </div>
  );
}
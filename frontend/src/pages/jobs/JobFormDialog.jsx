import { useState, useEffect } from "react";
import { useCreateJob, useUpdateJob,useEnhanceDescription,
  useGenerateRequirements,
  useEnhanceRequirements, } from "../../hooks/useJobs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button }   from "@/components/ui/button";
import { Input }    from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label }    from "@/components/ui/label";
import {
  Plus,
  Pencil,
  Sparkles,
  Wand2,
  RefreshCw,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { cn }    from "@/lib/utils";
import { toast } from "sonner";
import { LEVELS, LEVEL_STYLES } from "./LevelBadge";

const EMPTY_FORM = {
  title:           "",
  company:         "",
  description:     "",
  requirements:    "",
  seniority_level: "junior",
};

const RING_COLORS = {
  junior: "ring-sky-300",
  mid:    "ring-violet-300",
  senior: "ring-amber-300",
  lead:   "ring-rose-300",
};

function FieldError({ msg }) {
  if (!msg) return null;
  return <p className="text-xs text-red-500 mt-1">{msg}</p>;
}

function AIShimmer() {
  return (
    <div className="absolute inset-0 rounded-lg overflow-hidden pointer-events-none z-10">
      <div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-indigo-100/70 to-transparent"
        style={{ animation: "shimmer 1.4s infinite" }}
      />
    </div>
  );
}

function AIButton({ onClick, loading, done, variant = "enhance", disabled }) {
  const cfg = {
    enhance:    { Icon: Sparkles,  label: "Enhance",  active: "Enhancing…"    },
    generate:   { Icon: Wand2,     label: "Generate", active: "Generating…"   },
    regenerate: { Icon: RefreshCw, label: "Redo",     active: "Regenerating…" },
  }[variant];

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading || disabled}
      className={cn(
        "inline-flex items-center gap-1.5 text-[11px] font-semibold",
        "px-2.5 py-1 rounded-lg border transition-all select-none",
        done && !loading
          ? "text-emerald-700 bg-emerald-50 border-emerald-200"
          : "text-indigo-600 bg-indigo-50 border-indigo-100 hover:bg-indigo-100 hover:border-indigo-300",
        (loading || disabled) && "opacity-50 cursor-not-allowed pointer-events-none"
      )}
    >
      {loading ? (
        <Loader2 className="w-3 h-3 animate-spin" />
      ) : done ? (
        <CheckCircle2 className="w-3 h-3" />
      ) : (
        <cfg.Icon className="w-3 h-3" />
      )}
      {loading ? cfg.active : done ? "Applied!" : cfg.label}
    </button>
  );
}

export default function JobFormDialog({ open, onClose, initial = null }) {
  const isEdit    = !!initial;
  const createJob = useCreateJob();
  const updateJob = useUpdateJob();

  const enhanceDesc  = useEnhanceDescription();
  const generateReqs = useGenerateRequirements();
  const enhanceReqs  = useEnhanceRequirements();

  const [form,      setForm]      = useState(initial ?? EMPTY_FORM);
  const [errors,    setErrors]    = useState({});
  const [aiApplied, setAiApplied] = useState({ description: false, requirements: false });

  useEffect(() => {
    setForm(initial ?? EMPTY_FORM);
    setErrors({});
    setAiApplied({ description: false, requirements: false });
  }, [initial, open]);

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (field === "description" || field === "requirements") {
      setAiApplied((a) => ({ ...a, [field]: false }));
    }
  };

  const handleEnhanceDescription = async () => {
    if (!form.description.trim()) { toast.error("Write a description first"); return; }
    try {
      const result = await enhanceDesc.mutateAsync({
        title:       form.title   || "Untitled Role",
        company:     form.company || "Our Company",
        description: form.description,
      });
      setForm((f) => ({ ...f, description: result }));
      setAiApplied((a) => ({ ...a, description: true }));
      toast.success("Description enhanced!");
    } catch {
      toast.error("AI failed — check your Gemini API key");
    }
  };

  const handleGenerateRequirements = async () => {
    if (!form.description.trim()) { toast.error("Add a description first so AI has context"); return; }
    try {
      const result = await generateReqs.mutateAsync({
        title:       form.title   || "Untitled Role",
        company:     form.company || "Our Company",
        description: form.description,
      });
      setForm((f) => ({ ...f, requirements: result }));
      setAiApplied((a) => ({ ...a, requirements: true }));
      toast.success("Requirements generated!");
    } catch {
      toast.error("AI failed — check your Gemini API key");
    }
  };

  const handleEnhanceRequirements = async () => {
    if (!form.requirements.trim()) { toast.error("Write some requirements first"); return; }
    try {
      const result = await enhanceReqs.mutateAsync({
        title:        form.title || "Untitled Role",
        requirements: form.requirements,
      });
      setForm((f) => ({ ...f, requirements: result }));
      setAiApplied((a) => ({ ...a, requirements: true }));
      toast.success("Requirements enhanced!");
    } catch {
      toast.error("AI failed — check your Gemini API key");
    }
  };

  const validate = () => {
    const e = {};
    if (!form.title.trim())        e.title        = "Title is required";
    if (!form.company.trim())      e.company      = "Company is required";
    if (!form.description.trim())  e.description  = "Description is required";
    if (!form.requirements.trim()) e.requirements = "Requirements are required";
    return e;
  };

  const handleSubmit = async () => {
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setErrors({});
    try {
      if (isEdit) {
        await updateJob.mutateAsync({ id: initial.id, data: form });
        toast.success("Job updated!");
      } else {
        await createJob.mutateAsync(form);
        toast.success("Job created!");
      }
      onClose();
    } catch {
      toast.error(isEdit ? "Failed to update job" : "Failed to create job");
    }
  };

  const anyAILoading = enhanceDesc.isPending || generateReqs.isPending || enhanceReqs.isPending;
  const isSaving     = createJob.isPending   || updateJob.isPending;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { setErrors({}); onClose(); } }}>
      <DialogContent className="sm:max-w-[620px] max-h-[92vh] overflow-y-auto p-0">

        <DialogHeader className="px-6 pt-6 pb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-slate-900 flex items-center justify-center shrink-0">
              {isEdit ? <Pencil className="w-4 h-4 text-white" /> : <Plus className="w-4 h-4 text-white" />}
            </div>
            <div>
              <DialogTitle className="text-base font-semibold text-slate-900">
                {isEdit ? "Edit Job" : "Add New Job"}
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-indigo-400" />
                AI-assisted with Gemini
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="px-6 py-5 space-y-5">

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="title" className="text-xs font-medium text-slate-700">
                Job Title <span className="text-red-400">*</span>
              </Label>
              <Input
                id="title"
                placeholder="e.g. Frontend Engineer"
                value={form.title}
                onChange={set("title")}
                className={cn("h-9 text-sm", errors.title && "border-red-300 focus-visible:ring-red-300")}
              />
              <FieldError msg={errors.title} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="company" className="text-xs font-medium text-slate-700">
                Company <span className="text-red-400">*</span>
              </Label>
              <Input
                id="company"
                placeholder="e.g. Acme Corp"
                value={form.company}
                onChange={set("company")}
                className={cn("h-9 text-sm", errors.company && "border-red-300 focus-visible:ring-red-300")}
              />
              <FieldError msg={errors.company} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-700">Seniority Level</Label>
            <div className="flex gap-2 flex-wrap">
              {LEVELS.map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, seniority_level: lvl }))}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-medium border capitalize transition-all",
                    form.seniority_level === lvl
                      ? cn(LEVEL_STYLES[lvl], "ring-2 ring-offset-1", RING_COLORS[lvl])
                      : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
                  )}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <Label htmlFor="description" className="text-xs font-medium text-slate-700">
                Job Description <span className="text-red-400">*</span>
              </Label>
              <AIButton
                variant={aiApplied.description ? "regenerate" : "enhance"}
                onClick={handleEnhanceDescription}
                loading={enhanceDesc.isPending}
                done={aiApplied.description && !enhanceDesc.isPending}
                disabled={anyAILoading && !enhanceDesc.isPending}
              />
            </div>
            <div className="relative">
              <Textarea
                id="description"
                placeholder="Write a rough draft and let AI polish it, or type the full description yourself…"
                rows={5}
                value={form.description}
                onChange={set("description")}
                className={cn(
                  "text-sm resize-none transition-colors",
                  errors.description    && "border-red-300 focus-visible:ring-red-300",
                  aiApplied.description && !enhanceDesc.isPending && "border-emerald-300 bg-emerald-50/20",
                  enhanceDesc.isPending && "opacity-50"
                )}
              />
              {enhanceDesc.isPending && <AIShimmer />}
            </div>
            <FieldError msg={errors.description} />
          </div>

          {/* Requirements */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <Label htmlFor="requirements" className="text-xs font-medium text-slate-700">
                Requirements <span className="text-red-400">*</span>
              </Label>
              <div className="flex items-center gap-1.5">
                <AIButton
                  variant="generate"
                  onClick={handleGenerateRequirements}
                  loading={generateReqs.isPending}
                  done={false}
                  disabled={anyAILoading && !generateReqs.isPending}
                />
                {form.requirements.trim() && (
                  <AIButton
                    variant={aiApplied.requirements ? "regenerate" : "enhance"}
                    onClick={handleEnhanceRequirements}
                    loading={enhanceReqs.isPending}
                    done={aiApplied.requirements && !enhanceReqs.isPending}
                    disabled={anyAILoading && !enhanceReqs.isPending}
                  />
                )}
              </div>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Type your own, use{" "}
              <span className="text-indigo-500 font-medium">Generate</span> to create from description, or{" "}
              <span className="text-indigo-500 font-medium">Enhance</span> to polish what you wrote.
            </p>
            <div className="relative">
              <Textarea
                id="requirements"
                placeholder="List required skills, tools, years of experience… (or let AI generate them)"
                rows={5}
                value={form.requirements}
                onChange={set("requirements")}
                className={cn(
                  "text-sm resize-none transition-colors",
                  errors.requirements    && "border-red-300 focus-visible:ring-red-300",
                  aiApplied.requirements && !generateReqs.isPending && !enhanceReqs.isPending && "border-emerald-300 bg-emerald-50/20",
                  (generateReqs.isPending || enhanceReqs.isPending) && "opacity-50"
                )}
              />
              {(generateReqs.isPending || enhanceReqs.isPending) && <AIShimmer />}
            </div>
            <FieldError msg={errors.requirements} />
          </div>

        </div>

        <DialogFooter className="px-6 py-4 border-t border-slate-100 bg-slate-50/80 rounded-b-lg">
          {anyAILoading && (
            <div className="flex items-center gap-1.5 text-xs text-indigo-500 mr-auto animate-pulse">
              <Sparkles className="w-3.5 h-3.5" />
              Gemini is thinking…
            </div>
          )}
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSaving || anyAILoading}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={isSaving || anyAILoading}
            className="bg-slate-900 hover:bg-slate-700 text-white min-w-[110px]"
          >
            {isSaving
              ? (isEdit ? "Saving…" : "Creating…")
              : (isEdit ? "Save Changes" : "Create Job")}
          </Button>
        </DialogFooter>

      </DialogContent>
    </Dialog>
  );
}
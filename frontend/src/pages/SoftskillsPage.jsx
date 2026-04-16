// src/pages/SoftskillsPage.jsx
import { useMemo, useState } from "react";
import { Plus, Pencil, Trash2, Check, X, Brain, Search, ToggleLeft, ToggleRight } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCreateSoftskill, useDeleteSoftskill,
  useSoftskillsBank, useUpdateSoftskill,
} from "../hooks/useSoftskills";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

// ── Single skill row ──────────────────────────────────────────────────────────
function SkillRow({ item }) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    key: item.key, language: item.language,
    display_name: item.display_name, description: item.description, active: item.active,
  });

  const updateSkill = useUpdateSoftskill();
  const deleteSkill = useDeleteSoftskill();

  const save = async () => {
    try {
      await updateSkill.mutateAsync({ softskillId: item.id, payload: form });
      setEditing(false);
      toast.success("Soft skill updated");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to update soft skill");
    }
  };

  const remove = async () => {
    try {
      await deleteSkill.mutateAsync(item.id);
      toast.success("Soft skill deleted");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to delete soft skill");
    }
  };

  if (editing) {
    return (
      <div className="bg-indigo-50/40 border border-indigo-200 rounded-xl p-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <Input value={form.key} onChange={(e) => setForm((p) => ({ ...p, key: e.target.value }))} placeholder="key" className="h-8 text-xs" />
          <Input value={form.display_name} onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))} placeholder="Display name" className="h-8 text-xs" />
          <select value={form.language} onChange={(e) => setForm((p) => ({ ...p, language: e.target.value }))}
            className="h-8 rounded-lg border border-slate-200 bg-white px-2 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-300">
            <option value="en">English</option>
            <option value="fr">Français</option>
          </select>
        </div>
        <Textarea value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} rows={2} className="text-xs resize-none" />
        <div className="flex items-center justify-between">
          <label className="inline-flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
            <input type="checkbox" checked={form.active} onChange={(e) => setForm((p) => ({ ...p, active: e.target.checked }))} className="rounded" />
            {t("active")}
          </label>
          <div className="flex items-center gap-2">
            <button onClick={() => setEditing(false)} className="flex items-center gap-1 h-7 px-3 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-xs font-medium transition-colors">
              <X className="w-3 h-3" /> {t("cancel")}
            </button>
            <button onClick={save} disabled={updateSkill.isPending} className="flex items-center gap-1 h-7 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-colors">
              <Check className="w-3 h-3" /> {t("save")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      "group bg-white border rounded-xl p-4 hover:shadow-sm transition-all duration-150",
      item.active ? "border-slate-200" : "border-slate-100 opacity-60"
    )}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <code className="text-xs font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md">{item.key}</code>
            <span className={cn(
              "text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full",
              item.language === "en" ? "bg-sky-50 text-sky-600 border border-sky-200" : "bg-violet-50 text-violet-600 border border-violet-200"
            )}>
              {item.language}
            </span>
            <span className={cn(
              "text-[10px] font-semibold px-2 py-0.5 rounded-full border",
              item.active ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-slate-100 text-slate-500 border-slate-200"
            )}>
              {item.active ? t("active") : t("inactive")}
            </span>
          </div>
          <p className="text-sm font-semibold text-slate-800">{item.display_name}</p>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed line-clamp-2">{item.description}</p>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button onClick={() => setEditing(true)} className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button onClick={remove} className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SoftskillsPage() {
  const { t } = useI18n();
  const [language,     setLanguage]     = useState("en");
  const [showInactive, setShowInactive] = useState(false);
  const [search,       setSearch]       = useState("");
  const [showCreate,   setShowCreate]   = useState(false);

  const { data: skills = [], isLoading } = useSoftskillsBank({
    language,
    active: showInactive ? undefined : true,
  });

  const createSkill = useCreateSoftskill();
  const [createForm, setCreateForm] = useState({
    key: "", language: "en", display_name: "", description: "", active: true,
  });

  const sorted = useMemo(
    () => [...skills]
      .sort((a, b) => a.key.localeCompare(b.key))
      .filter((s) => {
        if (!search) return true;
        const q = search.toLowerCase();
        return s.key.includes(q) || s.display_name.toLowerCase().includes(q);
      }),
    [skills, search]
  );

  const create = async () => {
    if (!createForm.key.trim() || !createForm.display_name.trim()) {
      toast.error("Key and display name are required.");
      return;
    }
    try {
      await createSkill.mutateAsync(createForm);
      setCreateForm({ key: "", language, display_name: "", description: "", active: true });
      setShowCreate(false);
      toast.success("Soft skill created");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to create soft skill");
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{t("softSkillsBank")}</h1>
          <p className="text-sm text-slate-400 mt-0.5">{t("bilingualDefinitions")}</p>
        </div>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors shadow-sm shadow-indigo-200 shrink-0"
        >
          <Plus className="w-4 h-4" />
          {t("addSoftSkill")}
        </button>
      </div>

      {/* ── Create form ─────────────────────────────────────────────────── */}
      {showCreate && (
        <div className="bg-white rounded-2xl border border-indigo-200/60 shadow-[0_2px_12px_rgba(99,102,241,0.08)] p-5 space-y-4">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Brain className="w-3.5 h-3.5 text-white" />
            </div>
            <h2 className="text-sm font-semibold text-slate-800">{t("addSoftSkill")}</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">{t("keyPlaceholder")}</label>
              <Input value={createForm.key} onChange={(e) => setCreateForm((p) => ({ ...p, key: e.target.value }))}
                placeholder="e.g. team_collaboration" className="h-9 text-sm font-mono" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">{t("displayName")}</label>
              <Input value={createForm.display_name} onChange={(e) => setCreateForm((p) => ({ ...p, display_name: e.target.value }))}
                placeholder="e.g. Team Collaboration" className="h-9 text-sm" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Language</label>
              <select value={createForm.language} onChange={(e) => setCreateForm((p) => ({ ...p, language: e.target.value }))}
                className="w-full h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                <option value="en">English</option>
                <option value="fr">Français</option>
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600">{t("descriptionClassifier")}</label>
            <Textarea value={createForm.description} onChange={(e) => setCreateForm((p) => ({ ...p, description: e.target.value }))}
              rows={3} placeholder="Describe this soft skill and how the AI should classify it…" className="text-sm resize-none" />
          </div>

          <div className="flex items-center justify-between">
            <label className="inline-flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
              <input type="checkbox" checked={createForm.active} onChange={(e) => setCreateForm((p) => ({ ...p, active: e.target.checked }))} className="rounded" />
              {t("active")}
            </label>
            <div className="flex items-center gap-2">
              <button onClick={() => setShowCreate(false)} className="h-8 px-4 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-sm font-medium transition-colors">
                Cancel
              </button>
              <button onClick={create} disabled={createSkill.isPending} className="flex items-center gap-1.5 h-8 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors disabled:opacity-50">
                <Plus className="w-3.5 h-3.5" />
                {createSkill.isPending ? "Adding…" : t("add")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── List panel ──────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">

        {/* Toolbar */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-40 max-w-xs">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input type="text" placeholder="Search skills…" value={search} onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 h-8 rounded-lg border border-slate-200 bg-slate-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:bg-white transition-colors" />
          </div>

          {/* Language toggle */}
          <div className="flex items-center bg-slate-100 rounded-lg p-0.5">
            {["en", "fr"].map((l) => (
              <button key={l} onClick={() => setLanguage(l)} className={cn(
                "px-3 h-7 rounded-md text-xs font-semibold uppercase transition-all",
                language === l ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
              )}>
                {l === "en" ? "English" : "Français"}
              </button>
            ))}
          </div>

          {/* Show inactive */}
          <button
            onClick={() => setShowInactive((v) => !v)}
            className={cn(
              "flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-medium transition-all",
              showInactive ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
            )}
          >
            {showInactive ? <ToggleRight className="w-3.5 h-3.5" /> : <ToggleLeft className="w-3.5 h-3.5" />}
            {t("showInactive")}
          </button>

          <span className="ml-auto text-xs text-slate-400 tabular-nums">{sorted.length} skills</span>
        </div>

        {/* Skill list */}
        <div className="p-5">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-slate-100 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Skeleton className="h-5 w-24 rounded-md" />
                    <Skeleton className="h-5 w-10 rounded-full" />
                  </div>
                  <Skeleton className="h-4 w-40 rounded mb-1.5" />
                  <Skeleton className="h-3 w-full rounded" />
                </div>
              ))}
            </div>
          ) : !sorted.length ? (
            <div className="py-10 text-center">
              <Brain className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">{t("noSoftSkillsFound")}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {sorted.map((item) => <SkillRow key={item.id} item={item} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

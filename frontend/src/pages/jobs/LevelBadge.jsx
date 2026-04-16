import { cn } from "@/lib/utils";

export const LEVELS = ["junior", "mid", "senior", "lead"];

export const LEVEL_STYLES = {
  junior: "bg-sky-50     text-sky-700    border-sky-200",
  mid:    "bg-violet-50  text-violet-700 border-violet-200",
  senior: "bg-amber-50   text-amber-700  border-amber-200",
  lead:   "bg-rose-50    text-rose-700   border-rose-200",
};

export default function LevelBadge({ level }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize",
        LEVEL_STYLES[level] ?? "bg-slate-50 text-slate-500 border-slate-200"
      )}
    >
      {level ?? "—"}
    </span>
  );
}
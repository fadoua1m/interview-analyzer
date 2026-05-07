import { useDeleteJob } from "../../hooks/useJobs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { useI18n } from "@/lib/i18n";

export default function DeleteDialog({ job, open, onClose }) {
  const deleteJob = useDeleteJob();
  const { t } = useI18n();

  const handleDelete = async () => {
    try {
      await deleteJob.mutateAsync(job.id);
      toast.success(t("jobDeleted"));
      onClose();
    } catch {
      toast.error(t("failedDeleteJob"));
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-105">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-red-50 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-4 h-4 text-red-500" />
            </div>
            <DialogTitle className="text-base font-semibold text-slate-900">
              {t("deleteJob")}
            </DialogTitle>
          </div>
          <DialogDescription className="text-sm text-slate-500 pl-12">
            {t("deleteJobConfirm")}{" "}
            <span className="font-medium text-slate-700">"{job?.title}"</span>{" "}
            {t("atCompany")}{" "}
            <span className="font-medium text-slate-700">{job?.company}</span>?{" "}
            {t("actionCannotBeUndone")}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={deleteJob.isPending}
          >
            {t("cancel")}
          </Button>
          <Button
            size="sm"
            onClick={handleDelete}
            disabled={deleteJob.isPending}
            className="bg-red-500 hover:bg-red-600 text-white min-w-22.5"
          >
            {deleteJob.isPending ? t("deleting") : t("delete")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

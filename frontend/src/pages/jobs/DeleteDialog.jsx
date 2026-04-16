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

export default function DeleteDialog({ job, open, onClose }) {
  const deleteJob = useDeleteJob();

  const handleDelete = async () => {
    try {
      await deleteJob.mutateAsync(job.id);
      toast.success("Job deleted");
      onClose();
    } catch {
      toast.error("Failed to delete job");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-red-50 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-4 h-4 text-red-500" />
            </div>
            <DialogTitle className="text-base font-semibold text-slate-900">
              Delete Job
            </DialogTitle>
          </div>
          <DialogDescription className="text-sm text-slate-500 pl-12">
            Are you sure you want to delete{" "}
            <span className="font-medium text-slate-700">"{job?.title}"</span>{" "}
            at{" "}
            <span className="font-medium text-slate-700">{job?.company}</span>?
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={deleteJob.isPending}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleDelete}
            disabled={deleteJob.isPending}
            className="bg-red-500 hover:bg-red-600 text-white min-w-[90px]"
          >
            {deleteJob.isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
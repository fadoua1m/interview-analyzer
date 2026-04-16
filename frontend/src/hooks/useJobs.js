// src/hooks/useJobs.js
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "../api/client";

// ── Jobs CRUD ────────────────────────────────────────────────────────────────

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn:  () => client.get("/api/v1/jobs").then((r) => r.data),
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => client.post("/api/v1/jobs", data).then((r) => r.data),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useUpdateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) =>
      client.patch(`/api/v1/jobs/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => client.delete(`/api/v1/jobs/${id}`),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

// ── Jobs AI ──────────────────────────────────────────────────────────────────

export function useEnhanceDescription() {
  return useMutation({
    mutationFn: ({ title, company, description }) =>
      client
        .post("/api/v1/jobs/ai/enhance-description", { title, company, description })
        .then((r) => r.data.result),
  });
}

export function useGenerateRequirements() {
  return useMutation({
    mutationFn: ({ title, company, description }) =>
      client
        .post("/api/v1/jobs/ai/generate-requirements", { title, company, description })
        .then((r) => r.data.result),
  });
}

export function useEnhanceRequirements() {
  return useMutation({
    mutationFn: ({ title, requirements }) =>
      client
        .post("/api/v1/jobs/ai/enhance-requirements", { title, requirements })
        .then((r) => r.data.result),
  });
}
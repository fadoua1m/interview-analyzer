import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "../api/client";

export function useSoftskillsBank(params = {}) {
  return useQuery({
    queryKey: ["softskills", params],
    queryFn: () =>
      client
        .get("/api/v1/softskills", { params })
        .then((response) => response.data),
  });
}

export function useCreateSoftskill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) =>
      client.post("/api/v1/softskills", payload).then((response) => response.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["softskills"] });
    },
  });
}

export function useUpdateSoftskill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ softskillId, payload }) =>
      client
        .patch(`/api/v1/softskills/${softskillId}`, payload)
        .then((response) => response.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["softskills"] });
    },
  });
}

export function useDeleteSoftskill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (softskillId) => client.delete(`/api/v1/softskills/${softskillId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["softskills"] });
    },
  });
}

// src/hooks/useInterviews.js
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "../api/client";

function normalizeReportPayload(data = {}) {
  const em = data.emotion_metrics ?? {};
  const eng = data.engagement_metrics ?? {};
  const tm = data.text_metrics ?? {};
  return {
    interview_id:   data.interview_id ?? "",
    qa_pairs_count: Number(data.qa_pairs_count ?? 0),
    generated_at:   data.generated_at ?? null,

    text_metrics: {
      clarity_score:           Number(tm.clarity_score ?? 0),
      confidence_level:        tm.confidence_level ?? "unknown",
      relevance_score:         Number(tm.relevance_score ?? 0),
      relevance_per_question:  Array.isArray(tm.relevance_per_question) ? tm.relevance_per_question : [],
      per_question:            Array.isArray(tm.per_question) ? tm.per_question : [],
    },

    detected_skills: Array.isArray(data.detected_skills) ? data.detected_skills : [],

    emotion_metrics: {
      dominant_emotion:     em.dominant_emotion ?? "unknown",
      emotion_distribution: em.emotion_distribution ?? {},
      top_emotions:         em.top_emotions ?? {},
      emotion_timeline:     Array.isArray(em.emotion_timeline) ? em.emotion_timeline : [],
      positive_ratio:       Number(em.positive_ratio ?? 0),
      neutral_ratio:        Number(em.neutral_ratio ?? 0),
      negative_ratio:       Number(em.negative_ratio ?? 0),
      smile_rate:           Number(em.smile_rate ?? 0),
      stress_peak_count:    Number(em.stress_peak_count ?? 0),
      true_volatility:      Number(em.true_volatility ?? 0),
      confidence:           Number(em.confidence ?? 0),
    },

    engagement_metrics: {
      engagement_rate:     Number(eng.engagement_rate ?? 0),
      emotion_stability:   Number(eng.emotion_stability ?? 0),
      detection_quality:   Number(eng.detection_quality ?? 0),
      face_detection_rate: Number(eng.face_detection_rate ?? 0),
      focus_quality:       eng.focus_quality ?? "low",
    },

    overall_score:    Number(data.overall_score ?? 0),
    decision:         data.decision ?? "REVIEW",
    decision_reasons: Array.isArray(data.decision_reasons) ? data.decision_reasons : [],
    hr_summary:       data.hr_summary ?? "",
  };
}

// ── Dashboard summary ────────────────────────────────────────────────────────

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn:  () => client.get("/api/v1/interviews/dashboard-summary").then((r) => r.data),
  });
}

// ── Interviews ───────────────────────────────────────────────────────────────

export function useInterviews() {
  return useQuery({
    queryKey: ["interviews"],
    queryFn:  () => client.get("/api/v1/interviews").then((r) => r.data),
  });
}

export function useInterviewByJob(jobId) {
  return useQuery({
    queryKey: ["interviews", "job", jobId],
    queryFn:  () => client.get(`/api/v1/interviews/job/${jobId}`).then((r) => r.data),
    enabled:  !!jobId,
  });
}

export function useInterview(id) {
  return useQuery({
    queryKey: ["interviews", id],
    queryFn:  () => client.get(`/api/v1/interviews/${id}`).then((r) => r.data),
    enabled:  !!id,
  });
}

export function useCreateInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => client.post("/api/v1/interviews", data).then((r) => r.data),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["interviews"] }),
  });
}

export function useUpdateInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) =>
      client.patch(`/api/v1/interviews/${id}`, data).then((r) => r.data),
    onSuccess: (_result, variables) => {
      qc.invalidateQueries({ queryKey: ["interviews"] });
      if (variables?.id) {
        qc.invalidateQueries({ queryKey: ["interviews", variables.id] });
      }
    },
  });
}

export function useDeleteInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => client.delete(`/api/v1/interviews/${id}`),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["interviews"] }),
  });
}

// ── Questions CRUD ───────────────────────────────────────────────────────────

export function useCreateQuestion(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) =>
      client.post(`/api/v1/interviews/${interviewId}/questions`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

export function useUpdateQuestion(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ questionId, data }) =>
      client
        .patch(`/api/v1/interviews/${interviewId}/questions/${questionId}`, data)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

export function useDeleteQuestion(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (questionId) =>
      client.delete(`/api/v1/interviews/${interviewId}/questions/${questionId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

// ── Questions AI ─────────────────────────────────────────────────────────────

export function useGenerateQuestions(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    // POST /api/v1/interviews/{interviewId}/ai/generate-questions
    // payload: { title, company, interview_type, seniority_level, description, requirements, count }
    // returns: { questions: string[] }
    mutationFn: (payload) =>
      client
        .post(`/api/v1/interviews/${interviewId}/ai/generate-questions`, payload)
        .then((r) => r.data.questions),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId] }),
  });
}

export function useEnhanceQuestion(interviewId) {
  return useMutation({
    mutationFn: ({ questionId, payload }) =>
      client
        .post(
          `/api/v1/interviews/${interviewId}/questions/${questionId}/ai/enhance`,
          payload
        )
        .then((r) => r.data.result),
  });
}

export function useGenerateRubric(interviewId) {
  return useMutation({
    mutationFn: ({ questionId, payload }) =>
      client.post(
        `/api/v1/interviews/${interviewId}/questions/${questionId}/ai/generate-rubric`,
        payload
      ).then((r) => r.data.result),
  });
}

export function useEnhanceRubric(interviewId) {
  return useMutation({
    mutationFn: ({ questionId, payload }) =>
      client.post(
        `/api/v1/interviews/${interviewId}/questions/${questionId}/ai/enhance-rubric`,
        payload
      ).then((r) => r.data.result),
  });
}


export function useInterviewCandidates(interviewId) {
  return useQuery({
    queryKey: ["interviews", interviewId, "candidates"],
    queryFn: () =>
      client.get(`/api/v1/interviews/${interviewId}/candidates`).then((r) => r.data),
    enabled: !!interviewId,
  });
}


export function useAssignCandidate(interviewId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) =>
      client.post(`/api/v1/interviews/${interviewId}/candidates`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews", interviewId, "candidates"] }),
  });
}


export function useCandidateAccess(accessToken) {
  return useQuery({
    queryKey: ["candidate-access", accessToken],
    queryFn: () =>
      client.get(`/api/v1/interviews/candidate-access/${accessToken}`).then((r) => r.data),
    enabled: !!accessToken,
    retry: false,
  });
}


export function useSubmitCandidateVideo(accessToken) {
  return useMutation({
    mutationFn: (file) => {
      const formData = new FormData();
      formData.append("video", file);
      return client
        .post(`/api/v1/interviews/candidate-access/${accessToken}/submit`, formData)
        .then((r) => {
          const payload = r.data || {};
          return {
            ...payload,
            analysis: payload.analysis ? normalizeReportPayload(payload.analysis) : null,
          };
        });
    },
  });
}


export function useCandidateReport(interviewId, candidateId, enabled = true) {
  return useQuery({
    queryKey: ["interviews", interviewId, "candidates", candidateId, "report"],
    queryFn: () =>
      client
        .get(`/api/v1/interviews/${interviewId}/candidates/${candidateId}/report`)
        .then((r) => normalizeReportPayload(r.data || {})),
    enabled: !!interviewId && !!candidateId && enabled,
    retry: false,
  });
}


export function useTranslateAnalysisReport() {
  return useMutation({
    mutationFn: ({ report, targetLanguage }) =>
      client
        .post("/api/v1/analysis/translate-report", {
          report,
          target_language: targetLanguage,
        })
        .then((r) => normalizeReportPayload(r.data || {})),
  });
}


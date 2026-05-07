"""
Report Assembler
================
Combines TextAnalysisResult + VideoAnalysisResult into a final Report.
"""

import json
import logging
from datetime import datetime, timezone

from app.services.mistral_client import generate
from app.schemas.analysis import (
    QAPair,
    QuestionDetail,
    TextMetrics,
    EmotionMetrics,
    EmotionTimelinePoint,
    EngagementMetrics,
    Report,
    DetectedSkill,
)
from app.analysis_pipeline.text  import TextAnalysisResult
from app.analysis_pipeline.video import VideoAnalysisResult


logger = logging.getLogger(__name__)


def _lang_line(language: str) -> str:
    if language == "fr":
        return "IMPORTANT : Génère toutes tes décisions, raisons et résumés en français."
    return "IMPORTANT: Generate all decisions, reasons, and summaries in English."


# ── Utility helpers ─────────────────────────────────────────────────────────────

def _parse_json_safe(raw: str) -> dict:
    text = (raw or "").strip()
    fenced = text.find("```")
    if fenced != -1:
        end = text.find("```", fenced + 3)
        if end != -1:
            block = text[fenced + 3:end].strip()
            if block.lower().startswith("json"):
                block = block[4:].strip()
            text = block
    candidates = [text]
    obj_s = text.find("{")
    obj_e = text.rfind("}")
    if obj_s != -1 and obj_e > obj_s:
        candidates.append(text[obj_s:obj_e + 1])
    for c in candidates:
        c = c.strip()
        if not c:
            continue
        try:
            parsed = json.loads(c)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("Cannot parse JSON from model output", text, 0)



# ── Text Metrics Extraction ─────────────────────────────────────────────────────

def _extract_text_metrics(text_result: TextAnalysisResult | None) -> TextMetrics:
    if not text_result:
        return TextMetrics()

    clarity_list   = text_result.clarity_results or []
    relevance_dict = text_result.relevance_results or {}
    relevance_list = relevance_dict.get("per_question", [])

    relevance_per_question = [qs.score for qs in relevance_list]

    per_question: list[QuestionDetail] = []
    max_idx = max(len(clarity_list), len(relevance_list))
    for i in range(max_idx):
        cl  = clarity_list[i]   if i < len(clarity_list)   else None
        rel = relevance_list[i] if i < len(relevance_list) else None

        per_question.append(QuestionDetail(
            relevance_score=     rel.score             if rel else 0.0,
            directness_score=    rel.directness_score  if rel else None,
            depth_score=         rel.depth_score       if rel else None,
            rubric_fit_score=    rel.rubric_fit_score  if rel else None,
            reasoning=           rel.reasoning         if rel else "",
            clarity_score=       cl.clarity_score      if cl else 0.0,
            confidence_level=    cl.confidence_level   if cl else "unknown",
            star_coverage=       cl.star_coverage      if cl else "missing",
            brief_justification= cl.brief_justification if cl else "",
        ))

    return TextMetrics(
        clarity_score=          round(text_result.overall_clarity,   2),
        confidence_level=       text_result.overall_confidence,
        relevance_score=        round(text_result.overall_relevance, 2),
        relevance_per_question= relevance_per_question,
        per_question=           per_question,
    )


# ── Video Metrics Extraction ────────────────────────────────────────────────────

def _extract_video_metrics(
    video_result: VideoAnalysisResult | None,
) -> tuple["EmotionMetrics | None", "EngagementMetrics | None"]:
    if not video_result or not video_result.emotion_metrics:
        return None, None

    em  = video_result.emotion_metrics
    eng = video_result.engagement_metrics

    dist = {k: round(float(v), 1) for k, v in (em.emotion_distribution or {}).items()}
    top_emotions = dict(
        sorted(dist.items(), key=lambda x: x[1], reverse=True)[:3]
    )

    timeline: list[EmotionTimelinePoint] = []
    for i, point in enumerate(em.emotion_timeline or []):
        if isinstance(point, dict):
            timeline.append(EmotionTimelinePoint(
                timestamp_sec=    float(point.get("timestamp_sec", i)),
                dominant_emotion= str(point.get("dominant_emotion", "neutral")),
                confidence=       float(point.get("confidence", 0.0)),
                emotion_scores=   {
                    k: round(float(v), 4)
                    for k, v in (point.get("emotion_scores") or {}).items()
                },
            ))
        elif hasattr(point, "dominant_emotion"):
            timeline.append(point)

    emotion_metrics = EmotionMetrics(
        dominant_emotion=     em.dominant_emotion or "neutral",
        emotion_distribution= dist,
        top_emotions=         top_emotions,
        emotion_timeline=     timeline,
        positive_ratio=       round(getattr(em, "positive_ratio",    0.0), 2),
        neutral_ratio=        round(getattr(em, "neutral_ratio",     0.0), 2),
        negative_ratio=       round(getattr(em, "negative_ratio",    0.0), 2),
        smile_rate=           round(getattr(em, "smile_rate",        0.0), 2),
        stress_peak_count=    int(getattr(em,   "stress_peak_count", 0)),
        true_volatility=      round(getattr(em, "true_volatility",   0.0), 2),
        confidence=           round(getattr(em, "emotion_confidence", 0.0), 2),
    )

    engagement_metrics = None
    if eng:
        engagement_metrics = EngagementMetrics(
            engagement_rate=     round(getattr(eng, "engagement_rate",     0.0), 2),
            emotion_stability=   round(getattr(eng, "emotion_stability",   0.0), 2),
            detection_quality=   round(getattr(eng, "detection_quality",   0.0), 2),
            face_detection_rate= round(getattr(eng, "face_detection_rate", 0.0), 2),
            focus_quality=       getattr(eng, "focus_quality", "unknown") or "unknown",
        )

    return emotion_metrics, engagement_metrics


# ── Per-question summary for LLM ────────────────────────────────────────────────

def _per_question_context(
    qa_pairs:    list[QAPair],
    text_result: TextAnalysisResult | None,
) -> str:
    if not text_result or not qa_pairs:
        return "(no per-question data)"

    clarity_list   = text_result.clarity_results or []
    relevance_list = (text_result.relevance_results or {}).get("per_question", [])

    lines: list[str] = []
    for i, pair in enumerate(qa_pairs):
        cl  = clarity_list[i]   if i < len(clarity_list)   else None
        rel = relevance_list[i] if i < len(relevance_list) else None

        q_short = pair.question[:60].strip()
        parts: list[str] = []
        if rel:
            parts.append(f"relevance={rel.score:.1f}/10")
        if cl:
            parts.append(f"clarity={cl.clarity_score:.1f} conf={cl.confidence_level}")
        lines.append(f"  Q{i+1}: \"{q_short}\" → {', '.join(parts) if parts else 'no data'}")

    return "\n".join(lines)


# ── LLM Decision ────────────────────────────────────────────────────────────────

def _llm_decision(
    text_metrics:       TextMetrics,
    emotion_metrics:    "EmotionMetrics | None",
    engagement_metrics: "EngagementMetrics | None",
    detected_skills:    list[DetectedSkill],
    qa_pairs:           list[QAPair],
    text_result:        TextAnalysisResult | None = None,
    language:           str = "en",
) -> tuple[str, list[str], str, int]:
    relevance_score  = text_metrics.relevance_score
    clarity_score    = text_metrics.clarity_score
    confidence_level = text_metrics.confidence_level

    soft_skills_json = json.dumps(
        [{"name": s.name, "strength": s.strength, "quote": s.quote[:80]} for s in detected_skills[:6]],
        ensure_ascii=False,
    )

    per_q = _per_question_context(qa_pairs, text_result)

    if emotion_metrics and engagement_metrics:
        emotion_dist_json  = json.dumps(emotion_metrics.emotion_distribution, ensure_ascii=False)
        top_emotions_json  = json.dumps(emotion_metrics.top_emotions, ensure_ascii=False)
        engagement_rate    = engagement_metrics.engagement_rate
        emotion_stability  = engagement_metrics.emotion_stability
        face_detect_rate   = engagement_metrics.face_detection_rate
        detection_quality  = engagement_metrics.detection_quality
        focus_quality      = engagement_metrics.focus_quality
        dominant_emotion   = emotion_metrics.dominant_emotion
        emotion_conf       = emotion_metrics.confidence
        true_volatility    = emotion_metrics.true_volatility
        positive_ratio     = emotion_metrics.positive_ratio
        neutral_ratio      = emotion_metrics.neutral_ratio
        negative_ratio     = emotion_metrics.negative_ratio
        stress_peaks       = emotion_metrics.stress_peak_count
        n_timeline         = len(emotion_metrics.emotion_timeline)
    else:
        emotion_dist_json  = "{}"
        top_emotions_json  = "{}"
        engagement_rate    = 0.0
        emotion_stability  = 0.0
        face_detect_rate   = 0.0
        detection_quality  = 0.0
        focus_quality      = "unknown"
        dominant_emotion   = "unknown"
        emotion_conf       = 0.0
        true_volatility    = 0.0
        positive_ratio     = 0.0
        neutral_ratio      = 0.0
        negative_ratio     = 0.0
        stress_peaks       = 0
        n_timeline         = 0

    prompt = f"""{_lang_line(language)}

You are a principal HR technology evaluator with 15 years of talent assessment experience.
Your task: produce a calibrated hiring decision and a precise, evidence-backed HR narrative
from multimodal interview data (speech content + video behaviour).

━━━ CANDIDATE DATA ━━━

── TEXT SIGNALS (transcription + LLM scoring) ──
Questions answered     : {len(qa_pairs)}
Overall relevance      : {relevance_score:.1f} / 10  (directness + depth of answers)
Overall clarity        : {clarity_score:.1f} / 10  (structure, vocabulary, coherence)
Language confidence    : {confidence_level}         (high=owns outcomes, low=passive/vague)

Per-question breakdown:
{per_q}

Demonstrated competencies (strongest evidence first):
{soft_skills_json}

── BEHAVIOURAL SIGNALS (MTCNN + ViT-Face-Expression, frame-by-frame) ──
Face visibility        : {face_detect_rate:.0f}%   (% of frames with face detected)
Engagement score       : {engagement_rate:.0f}%   (composite: visibility + stability + quality)
Emotion stability      : {emotion_stability:.0f}%   (100 = perfectly composed throughout)
Detection confidence   : {detection_quality:.0f}%   (model confidence — proxy for video quality)
Focus quality          : {focus_quality}

Dominant emotion       : {dominant_emotion}
Positive affect ratio  : {positive_ratio:.0f}%   (happy + surprise frames)
Neutral ratio          : {neutral_ratio:.0f}%
Negative affect ratio  : {negative_ratio:.0f}%   (angry + sad + fearful + disgusted)
Emotional volatility   : {true_volatility:.1f}/100  (L2-distance based; 0=stable, 100=erratic)
Stress peaks           : {stress_peaks}            (sustained negative bursts ≥3 consecutive frames)
Frames analysed        : {n_timeline}

Emotion distribution   : {emotion_dist_json}
Top 3 emotions         : {top_emotions_json}

━━━ SCORING CALIBRATION ━━━
Score  Band        Criteria
85-100 Excellent   relevance ≥7.5 AND clarity ≥8 AND engagement ≥80% AND low negative affect
70-84  Good        relevance 6.5-7.5 AND clarity 7-8 AND engagement 65-80%, minor concerns
55-69  Borderline  relevance 5-6.5 OR clarity 5-7 OR engagement 45-65% OR mixed signals
40-54  Weak        relevance 4-5 OR clarity 4-5 OR engagement 30-45% OR notable flags
0-39   Poor        relevance <4 OR clarity <4 OR engagement <30% OR critical red flags

━━━ DECISION THRESHOLDS ━━━
PROCEED : relevance ≥6.5 AND clarity ≥7 AND engagement ≥65% AND dominant emotion not negative
REVIEW  : any metric borderline (4-6.5 text / 45-65% engagement) OR conflicting text-vs-video signals
REJECT  : relevance <4 OR clarity <4 OR engagement <30% OR dominant negative emotion with high volatility

━━━ OUTPUT FORMAT ━━━
Return ONLY valid JSON — no markdown, no extra keys:
{{
  "decision":      "PROCEED|REVIEW|REJECT",
  "overall_score": <integer 0-100>,
  "hr_summary":    "<paragraph>"
}}

━━━ HR SUMMARY REQUIREMENTS ━━━
Write exactly 4 sentences in a single paragraph. Be specific — always cite numbers.

Sentence 1 — OVERALL VERDICT
  State the decision and the score. Anchor it in the two or three most decisive metrics.
  Example pattern: "Candidate achieved [score]/100, driven by [metric] of [value] and [metric] of [value]."

Sentence 2 — STRONGEST EVIDENCE
  Name the single most compelling strength observed, with a concrete data point or quoted behaviour.
  If a strong/moderate competency was detected, cite it and the evidence fragment.

Sentence 3 — KEY RISK OR GAP
  Identify the most significant weakness — hedging language, vague answers, negative affect,
  low engagement, or missing depth. Be precise: state which question or metric exposed it.

Sentence 4 — BEHAVIOURAL PROFILE
  Synthesise the video signals into one sentence: emotional tone, stability, and focus quality.
  Flag any mismatch between text quality and behavioural signals (e.g. strong answers but high stress peaks).

Style rules:
  • Professional, factual, third-person, recruiter-ready — no filler phrases
  • No recommendations ("we suggest", "next step") — decision speaks for itself
  • Vary sentence openings — do not start every sentence with "The candidate"
  • If language is French, write entirely in French"""

    try:
        parsed = _parse_json_safe(generate(prompt))

        decision = str(parsed.get("decision", "REVIEW")).upper()
        if decision not in {"PROCEED", "REVIEW", "REJECT"}:
            decision = "REVIEW"

        try:
            overall_score = max(0, min(100, int(parsed.get("overall_score", 50))))
        except (ValueError, TypeError):
            overall_score = 50

        hr_summary = str(parsed.get("hr_summary", "")).strip()

        if relevance_score < 4.0:
            decision = "REJECT"
            hr_summary = (
                f"Candidate scored {overall_score}/100 with critically low relevance ({relevance_score:.1f}/10), "
                f"below the minimum threshold for progression. "
                f"Text clarity registered {clarity_score:.1f}/10, compounding the deficit. "
                f"Behavioural signals showed {dominant_emotion} as the dominant emotion with {engagement_rate:.0f}% engagement."
            )
        elif face_detect_rate > 0 and engagement_rate < 30:
            decision = "REJECT"
            hr_summary = (
                f"Candidate scored {overall_score}/100; video analysis flagged an engagement proxy of {engagement_rate:.0f}% — "
                f"below the 30% minimum threshold. "
                f"Text scores reached relevance {relevance_score:.1f}/10 and clarity {clarity_score:.1f}/10, "
                f"but the low behavioural presence ({face_detect_rate:.0f}% face detection rate, dominant emotion {dominant_emotion}) undermines confidence in the assessment."
            )
        elif relevance_score < 5.5 or clarity_score < 5.5:
            if decision == "PROCEED":
                decision = "REVIEW"
                hr_summary = (
                    f"Candidate scored {overall_score}/100 with borderline text quality — "
                    f"relevance {relevance_score:.1f}/10 and clarity {clarity_score:.1f}/10 fall below the threshold for automatic progression. "
                    f"Engagement proxy was {engagement_rate:.0f}% with {dominant_emotion} as the dominant emotion. "
                    f"The gap between video presence and text quality warrants manual HR review before a final decision."
                )

        if not hr_summary:
            hr_summary = (
                f"Candidate scored {overall_score}/100, anchored by relevance {relevance_score:.1f}/10 "
                f"and clarity {clarity_score:.1f}/10. "
                f"Engagement proxy reached {engagement_rate:.0f}% with {dominant_emotion} as the dominant emotional signal. "
                f"Overall text and video signals are consistent with the {decision.lower()} decision."
            )

    except Exception as e:
        logger.error("LLM decision failed: %s", e)
        decision = "REVIEW"
        overall_score = 50
        hr_summary = (
            f"Automated evaluation could not be completed due to an internal error. "
            f"Text signals: relevance {relevance_score:.1f}/10, clarity {clarity_score:.1f}/10. "
            f"Video signals: engagement {engagement_rate:.0f}%, dominant emotion {dominant_emotion}. "
            f"Manual HR review is required before a decision can be made."
        )

    return decision, [], hr_summary, overall_score


# ── Main Assembly ───────────────────────────────────────────────────────────────

def assemble(
    interview_id: str,
    qa_pairs:     list[QAPair],
    text_result:  TextAnalysisResult | None = None,
    video_result: VideoAnalysisResult | None = None,
    language:     str = "en",
) -> Report:
    """Assemble the final Report from text and video analysis results."""

    text_metrics                      = _extract_text_metrics(text_result)
    emotion_metrics, engagement_metrics = _extract_video_metrics(video_result)

    detected_skills: list[DetectedSkill] = [
        s for s in (text_result.competencies if text_result else [])
        if s.strength != "not_demonstrated"
    ]

    decision, reasons, summary, overall_score = _llm_decision(
        text_metrics, emotion_metrics, engagement_metrics,
        detected_skills, qa_pairs, text_result,
        language=language,
    )

    eng_str     = f"{engagement_metrics.engagement_rate:.0f}%" if engagement_metrics else "N/A"
    emotion_str = emotion_metrics.dominant_emotion if emotion_metrics else "unknown"
    logger.info(
        "id=%s clarity=%.1f relevance=%.1f engagement=%s emotion=%s decision=%s score=%d",
        interview_id, text_metrics.clarity_score, text_metrics.relevance_score,
        eng_str, emotion_str, decision, overall_score,
    )

    return Report(
        interview_id=   interview_id,
        qa_pairs_count= len(qa_pairs),
        generated_at=   datetime.now(timezone.utc),
        text_metrics=   text_metrics,
        detected_skills=detected_skills,
        emotion_metrics= emotion_metrics or EmotionMetrics(
            dominant_emotion="unknown",
            emotion_distribution={},
            top_emotions={},
            emotion_timeline=[],
            positive_ratio=0.0,
            neutral_ratio=0.0,
            negative_ratio=0.0,
            smile_rate=0.0,
            stress_peak_count=0,
            true_volatility=0.0,
            confidence=0.0,
        ),
        engagement_metrics=engagement_metrics or EngagementMetrics(
            engagement_rate=0.0,
            emotion_stability=0.0,
            detection_quality=0.0,
            face_detection_rate=0.0,
            focus_quality="unknown",
        ),
        overall_score=    float(overall_score),
        decision=         decision,
        decision_reasons= [],
        hr_summary=       summary,
    )

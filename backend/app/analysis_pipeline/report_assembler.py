"""
Report Assembler
================
Combines TextAnalysisResult + VideoAnalysisResult into a final Report.

Fixes applied (vs previous version):
  - emotion_m.distribution       → emotion_m.emotion_distribution
  - emotion_m.timeline           → emotion_m.emotion_timeline
  - emotion_m.volatility         → emotion_m.volatility_score
  - emotion_m.confidence         → emotion_m.emotion_confidence
  - face_detection_rate <= 0.5   → <= 50.0  (values are 0-100)
  - all :.0% formats on 0-100    → :.0f}%
  - gaze > 0.7 threshold         → > 70
  - fabricated "eye contact" obs → honest face-presence observation
  - LLM prompt enriched with per-question breakdown + behavioral context
"""

import json
from datetime import datetime, timezone

from app.services.mistral_client import generate
from app.schemas.analysis import (
    QAPair,
    TextMetrics,
    EmotionMetrics,
    EmotionTimelinePoint,
    EngagementMetrics,
    Report,
    DetectedSkill,
)
from app.analysis_pipeline.text  import TextAnalysisResult
from app.analysis_pipeline.video import VideoAnalysisResult


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


def _short_reason(text: str, max_words: int = 12) -> str:
    clean = " ".join(str(text or "").replace("\n", " ").split()).strip(" -•")
    if not clean:
        return "Manual HR review is recommended."
    words = clean.split()
    clean = " ".join(words[:max_words]).strip(" .,;") if len(words) > max_words else clean.strip(" .,;")
    return (clean[0].upper() + clean[1:] + ".") if clean else "Manual HR review is recommended."


# ── Text Metrics Extraction ─────────────────────────────────────────────────────

def _extract_text_metrics(text_result: TextAnalysisResult | None) -> TextMetrics:
    if not text_result:
        return TextMetrics(
            clarity_score=0.0,
            confidence_level="unknown",
            relevance_score=0.0,
            relevance_per_question=[],

        )



    relevance_per_question = [
        qs.score
        for qs in ((text_result.relevance_results or {}).get("per_question", []))
    ]

    return TextMetrics(
        clarity_score=round(text_result.overall_clarity, 2),
        confidence_level=text_result.overall_confidence,
        relevance_score=round(text_result.overall_relevance, 2),
        relevance_per_question=relevance_per_question,
    )


# ── Video Metrics Extraction ────────────────────────────────────────────────────

def _extract_video_metrics(
    video_result: VideoAnalysisResult | None,
) -> tuple["EmotionMetrics | None", "EngagementMetrics | None"]:
    """Convert internal video analysis objects to Pydantic schema objects.

    All internal emotion/engagement values are on 0-100 scale.
    """
    if not video_result or not video_result.emotion_metrics:
        return None, None

    em  = video_result.emotion_metrics   # internal EmotionMetrics
    eng = video_result.engagement_metrics  # internal EngagementMetrics

    # ── Emotion distribution (already %) ─────────────────────────────────────
    dist = {k: round(float(v), 1) for k, v in (em.emotion_distribution or {}).items()}

    top_emotions = dict(
        sorted(dist.items(), key=lambda x: x[1], reverse=True)[:3]
    )

    # ── Emotion timeline → Pydantic objects ──────────────────────────────────
    # Each point carries all 7 probabilities so the HR UI can render a
    # per-emotion time-series chart (Legara 2023 approach).
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

    # ── Schema EmotionMetrics ─────────────────────────────────────────────────
    # emotion_m.volatility_score   (was: emotion_m.volatility  — crashed)
    # emotion_m.emotion_confidence (was: emotion_m.confidence  — crashed)
    emotion_metrics = EmotionMetrics(
        dominant_emotion=    em.dominant_emotion or "neutral",
        emotion_distribution=dist,
        top_emotions=        top_emotions,
        emotion_timeline=    timeline,
        volatility=          round(em.volatility_score or 0.0, 2),
        positive_ratio=      round(em.positive_ratio   or 0.0, 2),
        confidence=          round(em.emotion_confidence or 0.0, 2),
    )

    # ── Schema EngagementMetrics ─────────────────────────────────────────────
    # face_detection_rate and gaze_consistency are 0-100; schema comment says
    # 0-1 but all downstream code (and the assembler) always treated them as 0-100.
    engagement_metrics = None
    if eng:
        engagement_metrics = EngagementMetrics(
            engagement_rate=     round(eng.engagement_rate     or 0.0, 2),
            head_stability=      round(eng.head_stability       or 0.0, 2),  # alias → emotion_stability
            gaze_consistency=    round(eng.gaze_consistency     or 0.0, 2),  # alias → face_detection_rate
            face_detection_rate= round(eng.face_detection_rate  or 0.0, 2),
            focus_quality=       eng.focus_quality or "unknown",
        )

    return emotion_metrics, engagement_metrics



# ── Per-question summary for LLM ────────────────────────────────────────────────

def _per_question_context(
    qa_pairs:      list[QAPair],
    text_result:   TextAnalysisResult | None,
) -> str:
    """Build a compact per-question breakdown for the LLM decision prompt."""
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
            parts.append(f"clarity={cl.clarity_score:.1f} conf={cl.confidence_level} STAR={cl.star_coverage}")
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
) -> tuple[str, list[str], str, int]:
    """Generate HR decision, overall score, reasons, and HR summary via LLM."""

    relevance_score  = text_metrics.relevance_score
    clarity_score    = text_metrics.clarity_score
    confidence_level = text_metrics.confidence_level

    soft_skills_json = json.dumps(
        [{"name": s.name, "strength": s.strength, "quote": s.quote[:80]} for s in detected_skills[:6]],
        ensure_ascii=False,
    )

    per_q = _per_question_context(qa_pairs, text_result)

    if emotion_metrics and engagement_metrics:
        emotion_dist_json = json.dumps(emotion_metrics.emotion_distribution, ensure_ascii=False)
        top_emotions_json = json.dumps(emotion_metrics.top_emotions, ensure_ascii=False)
        engagement_rate   = engagement_metrics.engagement_rate
        head_stability    = engagement_metrics.head_stability
        face_detect_rate  = engagement_metrics.face_detection_rate
        focus_quality     = engagement_metrics.focus_quality
        dominant_emotion  = emotion_metrics.dominant_emotion
        emotion_conf      = emotion_metrics.confidence         # 0-100
        volatility        = emotion_metrics.volatility         # 0-100
        positive_ratio    = emotion_metrics.positive_ratio     # 0-100
        n_timeline        = len(emotion_metrics.emotion_timeline)
    else:
        emotion_dist_json = "{}"
        top_emotions_json = "{}"
        engagement_rate   = 0.0
        head_stability    = 0.0
        face_detect_rate  = 0.0
        focus_quality     = "unknown"
        dominant_emotion  = "unknown"
        emotion_conf      = 0.0
        volatility        = 0.0
        positive_ratio    = 0.0
        n_timeline        = 0

    prompt = f"""You are a senior HR AI evaluator. Synthesize the multimodal interview data below into a hiring recommendation.

Return ONLY valid JSON (no markdown, no extra text):
{{
  "decision":         "PROCEED|REVIEW|REJECT",
  "overall_score":    <integer 0-100>,
  "decision_reasons": ["max 12-word reason 1", "reason 2", "reason 3"],
  "hr_summary":       "3-4 sentence paragraph. Sentence 1: overall fit + key score. Sentence 2: top strength with evidence. Sentence 3: main concern or risk. Sentence 4: recommended next action."
}}

━━━ TEXT ANALYSIS ━━━
Questions answered  : {len(qa_pairs)}
Relevance score     : {relevance_score:.1f} / 10
Clarity score       : {clarity_score:.1f} / 10
Language confidence : {confidence_level}

Per-question breakdown:
{per_q}

Detected soft skills:
{soft_skills_json}

━━━ VIDEO / BEHAVIORAL SIGNALS ━━━
(Source: MTCNN face detection + ViT-Face-Expression model.
 NOTE: head-pose and gaze data are NOT available — engagement is from face presence + emotion stability.)

Face detection rate      : {face_detect_rate:.0f}%
Engagement rate (proxy)  : {engagement_rate:.0f}%
Emotion stability index  : {head_stability:.0f}% (100 = perfectly stable)
Focus quality            : {focus_quality}

Dominant emotion         : {dominant_emotion}
Detection confidence     : {emotion_conf:.0f}%
Emotion volatility       : {volatility:.0f} / 100  (0=calm, 100=highly volatile)
Positive emotion ratio   : {positive_ratio:.0f}%
Timeline data points     : {n_timeline}

Emotion distribution     : {emotion_dist_json}
Top 3 emotions           : {top_emotions_json}

━━━ SCORING GUIDE ━━━
85-100  Excellent — relevance ≥7.5, clarity ≥8, engagement ≥80%, positive dominant, no red flags
70-84   Good      — relevance 6.5-7.5, clarity 7-8, engagement 70-80%, minor concerns
55-69   Borderline — relevance 5-6.5, clarity 5-7 OR moderate engagement (50-70%) OR flags present
40-54   Weak      — relevance 4-5, clarity 4-5 OR low engagement (30-50%) OR multiple flags
0-39    Poor      — relevance <4, clarity <4 OR face barely detected (<30%) OR critical flags

━━━ DECISION RULES ━━━
PROCEED : relevance ≥6.5, clarity ≥7, engagement ≥70%, positive/neutral dominant, no major flags
REVIEW  : borderline text (4-6.5) OR moderate engagement (50-70%) OR mixed / conflicting signals
REJECT  : relevance <4, clarity <4 OR engagement <30% OR critical red flags (e.g. blame_shifting + off_topic)

━━━ INSTRUCTIONS ━━━
• Cite specific numbers from the data in your reasons and summary
• The hr_summary must be exactly 3-4 sentences; professional, factual, recruiter-friendly
• overall_score must reflect BOTH text and video signals"""

    try:
        parsed = _parse_json_safe(generate(prompt))

        decision = str(parsed.get("decision", "REVIEW")).upper()
        if decision not in {"PROCEED", "REVIEW", "REJECT"}:
            decision = "REVIEW"

        reasons_raw = parsed.get("decision_reasons", [])
        decision_reasons = [
            _short_reason(str(r))
            for r in (reasons_raw if isinstance(reasons_raw, list) else [])
            if str(r).strip()
        ][:3]

        try:
            overall_score = max(0, min(100, int(parsed.get("overall_score", 50))))
        except (ValueError, TypeError):
            overall_score = 50

        # Hard overrides — when we change the decision, patch hr_summary too so
        # the report is self-consistent (LLM may have written "advance" when we REJECT).
        if relevance_score < 4.0:
            decision = "REJECT"
            decision_reasons = ["Relevance score critically low."] + decision_reasons[:2]
            hr_summary = (
                f"Candidate's answers showed critically low relevance ({relevance_score:.1f}/10), "
                f"below the minimum threshold for progression. "
                f"Text clarity was {clarity_score:.1f}/10. "
                f"Recommendation: do not advance to the next stage."
            )
        elif face_detect_rate > 0 and engagement_rate < 30:
            decision = "REJECT"
            decision_reasons = ["Insufficient engagement detected in video."] + decision_reasons[:2]
            hr_summary = (
                f"Video analysis detected a face in only {face_detect_rate:.0f}% of frames, "
                f"with an engagement proxy of {engagement_rate:.0f}% — below the 30% threshold. "
                f"Text scores: relevance {relevance_score:.1f}/10, clarity {clarity_score:.1f}/10. "
                f"Recommendation: do not advance without further verification."
            )
        elif relevance_score < 5.5 or clarity_score < 5.5:
            if decision == "PROCEED":
                decision = "REVIEW"
                hr_summary = (
                    f"Candidate showed borderline text quality (relevance {relevance_score:.1f}/10, "
                    f"clarity {clarity_score:.1f}/10) — below the threshold for automatic progression. "
                    f"Engagement proxy: {engagement_rate:.0f}%; dominant emotion: {dominant_emotion}. "
                    f"Recommendation: manual HR review before advancing."
                )
            decision_reasons = ["Borderline text quality signals."] + decision_reasons[:2]

        while len(decision_reasons) < 3:
            fallbacks = ["Manual HR review recommended.", "Assessment data provided.", "Next stage pending."]
            decision_reasons.append(fallbacks[len(decision_reasons) - 1])

        hr_summary = str(parsed.get("hr_summary", "")).strip()
        if not hr_summary:
            hr_summary = (
                f"Candidate scored {overall_score}/100 overall with relevance {relevance_score:.1f}/10 "
                f"and clarity {clarity_score:.1f}/10. "
                f"Engagement proxy: {engagement_rate:.0f}%; dominant emotion: {dominant_emotion}. "
                f"Recommended action: {'advance to next stage' if decision == 'PROCEED' else 'manual HR review' if decision == 'REVIEW' else 'do not advance'}."
            )

    except Exception as e:
        print(f"[Assembler] LLM decision failed: {e}")
        decision = "REVIEW"
        overall_score = 50
        decision_reasons = [
            "LLM evaluation unavailable — manual review required.",
            f"Text: relevance={relevance_score:.1f}/10, clarity={clarity_score:.1f}/10.",
            f"Video: engagement={engagement_rate:.0f}%, emotion={dominant_emotion}.",
        ]
        hr_summary = (
            f"Automated evaluation could not be completed. "
            f"Text signals: relevance={relevance_score:.1f}/10, clarity={clarity_score:.1f}/10. "
            f"Video signals: engagement={engagement_rate:.0f}%, dominant emotion={dominant_emotion}. "
            f"Manual HR review is strongly recommended."
        )

    return decision, decision_reasons[:3], hr_summary, overall_score


# ── Main Assembly ───────────────────────────────────────────────────────────────

def assemble(
    interview_id: str,
    qa_pairs:     list[QAPair],
    text_result:  TextAnalysisResult | None = None,
    video_result: VideoAnalysisResult | None = None,
) -> Report:
    """Assemble the final Report from text and video analysis results."""

    text_metrics                      = _extract_text_metrics(text_result)
    emotion_metrics, engagement_metrics = _extract_video_metrics(video_result)

    # Exclude not_demonstrated — competency_detector already drops them, but
    # guard here in case older data paths or tests still produce them.
    detected_skills: list[DetectedSkill] = [
        s for s in (text_result.competencies if text_result else [])
        if s.strength != "not_demonstrated"
    ]


    decision, reasons, summary, overall_score = _llm_decision(
        text_metrics, emotion_metrics, engagement_metrics,
        detected_skills, qa_pairs, text_result,
    )

    eng_str     = f"{engagement_metrics.engagement_rate:.0f}%" if engagement_metrics else "N/A"
    emotion_str = emotion_metrics.dominant_emotion if emotion_metrics else "unknown"
    print(
        f"[Assembler] id={interview_id} clarity={text_metrics.clarity_score:.1f} "
        f"relevance={text_metrics.relevance_score:.1f} engagement={eng_str} "
        f"emotion={emotion_str} decision={decision} score={overall_score}"
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
            volatility=0.0,
            positive_ratio=0.0,
            confidence=0.0,
        ),
        engagement_metrics=engagement_metrics or EngagementMetrics(
            engagement_rate=0.0,
            head_stability=0.0,
            gaze_consistency=0.0,
            face_detection_rate=0.0,
            focus_quality="unknown",
        ),
        overall_score=    float(overall_score),
        decision=         decision,
        decision_reasons= reasons,
        hr_summary=       summary,

    )

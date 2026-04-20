"""
Text Analyzer
=============
Main orchestrator for text analysis of interview responses.

Orchestrates:
  - clarity_analyzer       : Clarity score + language confidence + STAR coverage
  - relevance_scorer       : Relevance scoring (0-10, optional rubric)
  - competency_detector    : Soft skills/competency detection (language-aware)
"""

from app.schemas.analysis import QAPair
from app.analysis_pipeline.text.clarity_analyzer    import run as analyze_clarity,    ClarityAnalysis
from app.analysis_pipeline.text.relevance_scorer     import run as score_relevance
from app.analysis_pipeline.text.competency_detector  import run as detect_competencies


# ── Language detection ─────────────────────────────────────────────────────────

_FR_MARKERS = {
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "est", "sont", "était", "ont", "une", "des", "les", "sur",
    "dans", "avec", "pour", "mais", "que", "qui", "par", "ou",
    "mon", "ma", "mes", "ce", "cette", "ces", "donc", "aussi",
}
_EN_MARKERS = {
    "i", "the", "a", "is", "was", "were", "have", "had",
    "my", "our", "we", "it", "in", "on", "to", "of",
    "and", "but", "that", "this", "with", "for", "by", "at",
    "he", "she", "they", "you", "as", "an", "so",
}


def _detect_language(text: str) -> str:
    """Return 'fr' or 'en' based on token frequency in the given text."""
    tokens = text.lower().split()
    if not tokens:
        return "en"
    fr_hits = sum(1 for t in tokens if t in _FR_MARKERS)
    en_hits = sum(1 for t in tokens if t in _EN_MARKERS)
    if fr_hits > en_hits + 1:
        return "fr"
    return "en"


# ── Result class ───────────────────────────────────────────────────────────────

class TextAnalysisResult:
    """Complete text analysis output for all interview answers."""

    def __init__(
        self,
        qa_pairs:          list[QAPair],
        clarity_results:   list[ClarityAnalysis] | None = None,
        relevance_results: dict | None = None,
        competencies:      list | None = None,
        detected_language: str  = "en",
    ):
        self.qa_pairs          = qa_pairs
        self.clarity_results   = clarity_results   or []
        self.relevance_results = relevance_results or {"per_question": [], "overall_score": 0.0}
        self.competencies      = competencies      or []
        self.detected_language = detected_language

        self.overall_clarity    = self._calc_clarity_score()
        self.overall_confidence = self._calc_confidence_level()
        self.overall_relevance  = self._calc_relevance_score()

    def _calc_clarity_score(self) -> float:
        scored = [r for r in self.clarity_results if not r.skipped]
        if not scored:
            return 0.0
        return round(sum(r.clarity_score for r in scored) / len(scored), 2)

    def _calc_confidence_level(self) -> str:
        scored = [r for r in self.clarity_results if not r.skipped]
        if not scored:
            return "unknown"
        levels     = [r.confidence_level for r in scored]
        high_count = levels.count("high")
        med_count  = levels.count("medium")
        n          = len(levels)
        if high_count > n / 2:
            return "high"
        elif med_count >= n / 3:
            return "medium"
        return "low"

    def _calc_relevance_score(self) -> float:
        return self.relevance_results.get("overall_score", 0.0)


# ── Public API ─────────────────────────────────────────────────────────────────

def analyze_text(qa_pairs: list[QAPair], language: str | None = None) -> TextAnalysisResult:
    """Analyze interview text responses across all dimensions.

    Args:
        qa_pairs: list of QAPair objects with question and answer
        language: "en" or "fr". If None, auto-detected from candidate answers.

    Returns:
        TextAnalysisResult with clarity, relevance, and competency analysis.
    """
    if not qa_pairs:
        return TextAnalysisResult(qa_pairs=[], detected_language=language or "en")

    if language is None:
        sample = " ".join((p.answer or "") for p in qa_pairs if p.answer)[:3000]
        language = _detect_language(sample)
        print(f"[TextAnalyzer] Auto-detected language: {language}")
    else:
        language = language.strip().lower()
        if language not in {"en", "fr"}:
            language = "en"

    clarity_results   = analyze_clarity(qa_pairs)
    relevance_results = score_relevance(qa_pairs)
    competencies      = detect_competencies(qa_pairs, language=language)

    return TextAnalysisResult(
        qa_pairs=qa_pairs,
        clarity_results=clarity_results,
        relevance_results=relevance_results,
        competencies=competencies,
        detected_language=language,
    )

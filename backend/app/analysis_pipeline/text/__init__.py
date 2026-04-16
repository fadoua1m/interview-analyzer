"""
Text Analysis Module
====================
Modular analysis of interview answers with clear separation of concerns.

Modules:
  - clarity_analyzer   : Clarity score + language confidence + STAR coverage
  - relevance_scorer   : Relevance scoring (0-10, optional rubric)
  - competency_detector: Soft skills/competency detection (language-aware)
  - text_analyzer      : Main orchestrator
"""

from app.analysis_pipeline.text.clarity_analyzer    import run as analyze_clarity,    ClarityAnalysis
from app.analysis_pipeline.text.relevance_scorer     import run as score_relevance,    RelevanceScore
from app.analysis_pipeline.text.competency_detector  import run as detect_competencies
from app.analysis_pipeline.text.text_analyzer        import analyze_text,              TextAnalysisResult

__all__ = [
    "analyze_clarity",
    "score_relevance",
    "detect_competencies",
    "analyze_text",
    "ClarityAnalysis",
    "RelevanceScore",
    "TextAnalysisResult",
]

"""
explain_report.py
=================
Script de présentation pédagogique du rapport d'analyse d'entretien.

Usage:
    python explain_report.py                        # explique les métriques (mode doc)
    python explain_report.py --report report.json   # explique un rapport concret
    python explain_report.py --lang en              # en anglais

Objectif : fournir une explication claire de chaque métrique à l'encadrant.
"""

import json
import sys
import argparse
from pathlib import Path


# ── Palette de couleurs ANSI (terminal) ──────────────────────────────────────

BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BLUE   = "\033[34m"
MAGENTA= "\033[35m"
RESET  = "\033[0m"

def h1(text):  print(f"\n{BOLD}{CYAN}{'═'*70}{RESET}\n{BOLD}{CYAN}  {text}{RESET}\n{BOLD}{CYAN}{'═'*70}{RESET}")
def h2(text):  print(f"\n{BOLD}{BLUE}  ▶ {text}{RESET}")
def h3(text):  print(f"\n{BOLD}    • {text}{RESET}")
def info(text):print(f"      {DIM}{text}{RESET}")
def val(label, v, color=GREEN): print(f"      {label:<30} {color}{BOLD}{v}{RESET}")
def sep():     print(f"  {DIM}{'─'*66}{RESET}")


# ── Documentation des métriques ───────────────────────────────────────────────

METRICS_DOC_FR = {

    "DÉCISION RH": {
        "decision": (
            "PROCEED / REVIEW / REJECT",
            "Décision automatique de passage à l'étape suivante.\n"
            "      PROCEED = le candidat remplit les seuils minimaux (pertinence ≥6.5, clarté ≥7, engagement ≥70 %).\n"
            "      REVIEW  = signaux ambivalents — un RH doit examiner manuellement.\n"
            "      REJECT  = pertinence <4/10 OU engagement <30 % OU signaux critiques détectés.",
        ),
        "overall_score": (
            "Score global   [0–100]",
            "Combinaison pondérée du texte ET de la vidéo, calculée par le LLM (Mistral).\n"
            "      ≥85 = Excellent · 70-84 = Bon · 55-69 = Limite · 40-54 = Faible · <40 = Insuffisant.",
        ),
        "hr_summary": (
            "Résumé RH",
            "Paragraphe de 3 phrases généré par l'IA :\n"
            "      Phrase 1 — Adéquation globale + score clé.\n"
            "      Phrase 2 — Point fort principal avec citation ou chiffre.\n"
            "      Phrase 3 — Risque ou point de vigilance principal.",
        ),
    },

    "ANALYSE TEXTUELLE (LLM sur transcription audio)": {
        "clarity_score": (
            "Clarté   [0–10]",
            "Évalue la qualité de communication orale : structure logique, vocabulaire précis,\n"
            "      absence de remplissage (« euh », « donc »). Pénalise le hors-sujet et la répétition.\n"
            "      Source : modèle Mistral analysant chaque réponse transcrite via Whisper.",
        ),
        "relevance_score": (
            "Pertinence   [0–10]",
            "Mesure dans quelle mesure la réponse adresse DIRECTEMENT la question posée ET\n"
            "      apporte des preuves concrètes (chiffres, exemples STAR).\n"
            "      Score = moyenne(Directivité + Profondeur) / 2 par question.",
        ),
        "confidence_level": (
            "Confiance linguistique   [high/medium/low]",
            "Indicateur de maîtrise du langage de l'entretien :\n"
            "      high   → verbes à la 1ère personne décisifs (« j'ai livré », « j'ai conçu »).\n"
            "      medium → quelques hésitations, usage de « nous » sans clarifier le rôle.\n"
            "      low    → langage passif, hésitations fréquentes, pas d'exemples personnels.",
        ),
        "star_coverage": (
            "Couverture STAR   [full/partial/missing]",
            "Méthode STAR = Situation → Tâche → Action → Résultat.\n"
            "      Évalue si le candidat structure ses réponses avec des anecdotes mesurables.\n"
            "      full = les 4 éléments présents · partial = 2-3 · missing = 0-1.",
        ),
        "per_question": (
            "Détail par question",
            "Pour chaque question : pertinence, clarté, STAR, confiance, justification concise.\n"
            "      Permet au RH de voir exactement sur quelle(s) question(s) le candidat a échoué.",
        ),
    },

    "SOFT SKILLS DÉTECTÉES (LLM multi-passes)": {
        "detected_skills": (
            "Compétences comportementales",
            "Détectées automatiquement dans chaque réponse par rapport à la banque de soft skills\n"
            "      définie par le recruteur (ex. communication, leadership, esprit d'équipe).\n"
            "      Chaque compétence est cotée :\n"
            "        strong   → exemple concret AVEC résultat mesurable.\n"
            "        moderate → exemple clair SANS résultat quantifié.\n"
            "        weak     → mentionné mais sans preuve réelle.\n"
            "      Une citation verbatim de la réponse est fournie comme justification.",
        ),
    },

    "ANALYSE VIDÉO — ÉMOTIONS (ViT-Face-Expression)": {
        "dominant_emotion": (
            "Émotion dominante",
            "Émotion la plus fréquente sur l'ensemble des frames analysées.\n"
            "      Modèle utilisé : ViT-Face-Expression (7 classes : happy, neutral, sad,\n"
            "      angry, fearful, disgusted, surprised).",
        ),
        "positive_ratio": (
            "Ratio positif   [0–100 %]",
            "Pourcentage de frames où l'émotion dominante est happy OU surprise.\n"
            "      Indicateur de dynamisme et d'enthousiasme pendant l'entretien.\n"
            "      (N'inclut PAS neutral — ce qui était le défaut dans la v1.)",
        ),
        "neutral_ratio": (
            "Ratio neutre   [0–100 %]",
            "Pourcentage de frames avec émotion neutre.\n"
            "      Une valeur élevée signifie un candidat calme et professionnel.\n"
            "      Combiné avec positive_ratio, donne l'image de sérénité globale.",
        ),
        "negative_ratio": (
            "Ratio négatif   [0–100 %]",
            "Pourcentage de frames avec une émotion négative (angry, sad, fearful, disgusted).\n"
            "      Valeur élevée → possible stress, inconfort, ou mauvaise adéquation culturelle.",
        ),
        "true_volatility": (
            "Volatilité émotionnelle L2   [0–100]",
            "Mesure la variation de la DISTRIBUTION complète d'émotions entre frames consécutives.\n"
            "      Calcul : distance L2 entre les vecteurs de probabilité (7 dimensions) normalisée.\n"
            "      Physiquement supérieure au simple comptage de changements d'étiquette (ancienne méthode).\n"
            "      0 = état émotionnel parfaitement stable · 100 = instabilité maximale.",
        ),
        "stress_peak_count": (
            "Pics de stress   [entier]",
            "Nombre de séquences d'au moins 3 frames consécutives avec une émotion négative.\n"
            "      Un pic = une bouffée soutenue de stress/inconfort (pas juste un flash).\n"
            "      Plus fiable qu'un ratio global pour détecter les moments critiques.",
        ),
        "confidence": (
            "Confiance de détection   [0–100 %]",
            "Probabilité moyenne du modèle sur l'émotion dominante par frame détectée.\n"
            "      Valeur faible → mauvais éclairage, visage flou, ou caméra mal positionnée.",
        ),
    },

    "ANALYSE VIDÉO — ENGAGEMENT (Signaux composites)": {
        "engagement_rate": (
            "Taux d'engagement   [0–100]",
            "Score composite calculé par :\n"
            "      face_detection_rate × 0.40\n"
            "    + emotion_stability   × 0.40\n"
            "    + detection_quality  × 0.20\n"
            "      Interprétation : ≥70 % = engagé · 42-70 % = modéré · <42 % = faible.",
        ),
        "face_detection_rate": (
            "Taux de détection du visage   [0–100 %]",
            "Pourcentage de frames où MTCNN a détecté un visage.\n"
            "      Proxy de présence physique et de visibilité devant la caméra.\n"
            "      <30 % = problème technique ou candidat souvent hors champ.",
        ),
        "emotion_stability": (
            "Stabilité émotionnelle   [0–100]",
            "100 minus la fraction de paires de frames consécutives avec un changement d'étiquette × 100.\n"
            "      Mesure la constance de l'état émotionnel : un candidat composé aura ≥70.\n"
            "      Faible → expressions très changeantes, possible nervosité ou agitation.",
        ),
        "detection_quality": (
            "Qualité de détection   [0–100 %]",
            "Confiance moyenne du modèle ViT lorsqu'un visage est détecté.\n"
            "      Proxy de la qualité de l'image (éclairage, résolution, netteté).\n"
            "      Faible → conditions d'enregistrement sous-optimales.",
        ),
        "focus_quality": (
            "Qualité de concentration   [low/medium/high]",
            "Seuils appliqués sur le taux d'engagement :\n"
            "      high   → engagement ≥70 %\n"
            "      medium → 42 % ≤ engagement < 70 %\n"
            "      low    → engagement < 42 %",
        ),
    },
}


METRICS_DOC_EN = {
    "HR DECISION": {
        "decision": (
            "PROCEED / REVIEW / REJECT",
            "Automated hiring recommendation.\n"
            "      PROCEED = candidate meets minimum thresholds (relevance ≥6.5, clarity ≥7, engagement ≥70%).\n"
            "      REVIEW  = mixed signals — manual HR review required.\n"
            "      REJECT  = relevance <4/10 OR engagement <30% OR critical red flags.",
        ),
        "overall_score": (
            "Overall score   [0–100]",
            "Weighted combination of text AND video signals, computed by Mistral LLM.\n"
            "      ≥85 Excellent · 70-84 Good · 55-69 Borderline · 40-54 Weak · <40 Poor.",
        ),
        "hr_summary": (
            "HR Summary",
            "3-sentence paragraph generated by AI:\n"
            "      Sentence 1 — Overall fit + key score.\n"
            "      Sentence 2 — Top strength with quote or number.\n"
            "      Sentence 3 — Main risk or concern.",
        ),
    },
}


def print_doc(lang: str = "fr"):
    doc = METRICS_DOC_FR if lang == "fr" else METRICS_DOC_EN

    if lang == "fr":
        h1("DOCUMENTATION DU RAPPORT D'ANALYSE — AI Analyzer")
        print(f"\n  {DIM}Ce document explique chaque métrique produite par la pipeline d'analyse.\n"
              f"  Source : transcription Whisper → Mistral LLM (texte) + ViT-Face-Expression (vidéo).{RESET}")
    else:
        h1("ANALYSIS REPORT DOCUMENTATION — AI Analyzer")

    for section, metrics in doc.items():
        h2(section)
        sep()
        for key, (label, description) in metrics.items():
            h3(f"{YELLOW}{key}{RESET}  —  {label}")
            for line in description.split("\n"):
                info(line)
        print()


# ── Explications d'un rapport concret ────────────────────────────────────────

def _decision_color(d: str):
    return GREEN if d == "PROCEED" else YELLOW if d == "REVIEW" else RED

def _score_color(v: float):
    return GREEN if v >= 70 else YELLOW if v >= 50 else RED

def _pct_color(v: float):
    return GREEN if v >= 60 else YELLOW if v >= 35 else RED

def print_report_explained(report: dict, lang: str = "fr"):
    h1("RAPPORT D'ANALYSE — EXPLICATION DÉTAILLÉE" if lang == "fr" else "ANALYSIS REPORT — DETAILED EXPLANATION")

    # ── Décision ─────────────────────────────────────────────────────────────
    h2("DÉCISION RH" if lang == "fr" else "HR DECISION")
    sep()
    decision = report.get("decision", "REVIEW")
    score    = report.get("overall_score", 0)
    dc       = _decision_color(decision)
    sc       = _score_color(score)

    val("Décision :" if lang == "fr" else "Decision :", decision, dc)
    val("Score global :" if lang == "fr" else "Overall score :", f"{score}/100", sc)

    reasons = report.get("decision_reasons", [])
    if reasons:
        print(f"\n      {'Raisons :' if lang == 'fr' else 'Reasons :'}")
        for r in reasons:
            print(f"        {YELLOW}·{RESET} {r}")

    hr = report.get("hr_summary", "")
    if hr:
        print(f"\n      {'Résumé RH :' if lang == 'fr' else 'HR Summary :'}")
        for sentence in hr.split(". "):
            s = sentence.strip().rstrip(".")
            if s:
                print(f"        {DIM}→ {s}.{RESET}")

    # ── Texte ─────────────────────────────────────────────────────────────────
    h2("ANALYSE TEXTUELLE" if lang == "fr" else "TEXT ANALYSIS")
    sep()
    tm = report.get("text_metrics", {})

    cs = tm.get("clarity_score", 0)
    rs = tm.get("relevance_score", 0)
    cl = tm.get("confidence_level", "unknown")

    val("Clarté :" if lang == "fr" else "Clarity :",       f"{cs:.1f}/10",  _score_color(cs * 10))
    val("Pertinence :" if lang == "fr" else "Relevance :", f"{rs:.1f}/10",  _score_color(rs * 10))
    val("Confiance :" if lang == "fr" else "Confidence :", cl.upper(),
        GREEN if cl == "high" else YELLOW if cl == "medium" else RED)

    pq_list = tm.get("per_question", [])
    if pq_list:
        print(f"\n      {'Détail par question :' if lang == 'fr' else 'Per-question detail :'}")
        for i, pq in enumerate(pq_list):
            star = pq.get("star_coverage", "missing")
            star_c = GREEN if star == "full" else YELLOW if star == "partial" else RED
            print(f"\n        Q{i+1}")
            print(f"          Pertinence : {_score_color(pq.get('relevance_score',0)*10)}{pq.get('relevance_score',0):.1f}/10{RESET}  "
                  f"Clarté : {_score_color(pq.get('clarity_score',0)*10)}{pq.get('clarity_score',0):.1f}/10{RESET}  "
                  f"STAR : {star_c}{star.upper()}{RESET}")
            justif = pq.get("brief_justification") or pq.get("reasoning", "")
            if justif:
                print(f"          {DIM}↳ {justif[:100]}{RESET}")

    # ── Soft skills ───────────────────────────────────────────────────────────
    skills = report.get("detected_skills", [])
    if skills:
        h2("SOFT SKILLS DÉTECTÉES" if lang == "fr" else "DETECTED SOFT SKILLS")
        sep()
        for sk in skills:
            label = sk.get("display_name") or sk.get("name", "").replace("_", " ")
            strength = sk.get("strength", "weak")
            sc2 = GREEN if strength == "strong" else CYAN if strength == "moderate" else YELLOW
            print(f"      {sc2}{BOLD}{label.capitalize():<25}{RESET}  [{sc2}{strength}{RESET}]")
            if sk.get("quote"):
                print(f"        {DIM}« {sk['quote'][:90]} »{RESET}")

    # ── Émotions ──────────────────────────────────────────────────────────────
    h2("ANALYSE ÉMOTIONNELLE" if lang == "fr" else "EMOTION ANALYSIS")
    sep()
    em = report.get("emotion_metrics", {})

    val("Émotion dominante :" if lang == "fr" else "Dominant emotion :", em.get("dominant_emotion", "—").capitalize())
    val("Ratio positif :"     if lang == "fr" else "Positive ratio :",   f"{em.get('positive_ratio', 0):.0f}%", _pct_color(em.get("positive_ratio", 0)))
    val("Ratio neutre :"      if lang == "fr" else "Neutral ratio :",    f"{em.get('neutral_ratio', 0):.0f}%",  _pct_color(em.get("neutral_ratio", 0)))
    val("Ratio négatif :"     if lang == "fr" else "Negative ratio :",   f"{em.get('negative_ratio', 0):.0f}%",
        RED if em.get("negative_ratio", 0) > 30 else YELLOW if em.get("negative_ratio", 0) > 15 else GREEN)
    val("Volatilité L2 :"     if lang == "fr" else "L2 Volatility :",    f"{em.get('true_volatility', 0):.1f}/100",
        GREEN if em.get("true_volatility", 0) < 30 else YELLOW if em.get("true_volatility", 0) < 60 else RED)
    val("Pics de stress :"    if lang == "fr" else "Stress peaks :",     str(em.get("stress_peak_count", 0)),
        GREEN if em.get("stress_peak_count", 0) == 0 else YELLOW if em.get("stress_peak_count", 0) < 3 else RED)
    val("Confiance détection :" if lang == "fr" else "Detection confidence :", f"{em.get('confidence', 0):.0f}%",
        _pct_color(em.get("confidence", 0)))

    top = em.get("top_emotions", {})
    if top:
        print(f"\n      {'Top émotions :' if lang == 'fr' else 'Top emotions :'}")
        for emo, pct in sorted(top.items(), key=lambda x: x[1], reverse=True):
            bar_len = int(pct / 5)
            print(f"        {emo:<12} {'█'*bar_len}{DIM}{'░'*(20-bar_len)}{RESET}  {pct:.0f}%")

    # ── Engagement ────────────────────────────────────────────────────────────
    h2("ENGAGEMENT (VIDÉO)" if lang == "fr" else "ENGAGEMENT (VIDEO)")
    sep()
    eng = report.get("engagement_metrics", {})

    er  = eng.get("engagement_rate", 0)
    fdr = eng.get("face_detection_rate", 0)
    es  = eng.get("emotion_stability", 0)
    dq  = eng.get("detection_quality", 0)
    fq  = eng.get("focus_quality", "low")

    val("Taux d'engagement :"      if lang == "fr" else "Engagement rate :",    f"{er:.0f}%",  _score_color(er))
    val("Détection du visage :"    if lang == "fr" else "Face detection :",     f"{fdr:.0f}%", _pct_color(fdr))
    val("Stabilité émotionnelle :" if lang == "fr" else "Emotion stability :",  f"{es:.0f}%",  _pct_color(es))
    val("Qualité de détection :"   if lang == "fr" else "Detection quality :",  f"{dq:.0f}%",  _pct_color(dq))
    val("Concentration :"          if lang == "fr" else "Focus quality :",      fq.upper(),
        GREEN if fq == "high" else YELLOW if fq == "medium" else RED)

    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Explique les métriques du rapport d'analyse d'entretien AI Analyzer"
    )
    parser.add_argument("--report", "-r", type=str, default=None,
                        help="Chemin vers un fichier JSON de rapport (optionnel)")
    parser.add_argument("--lang", "-l", type=str, default="fr", choices=["fr", "en"],
                        help="Langue d'affichage (fr par défaut)")
    parser.add_argument("--doc-only", "-d", action="store_true",
                        help="Affiche uniquement la documentation des métriques")
    args = parser.parse_args()

    print_doc(args.lang)

    if args.doc_only or not args.report:
        return

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"{RED}Fichier introuvable : {args.report}{RESET}")
        sys.exit(1)

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    print_report_explained(report, args.lang)


if __name__ == "__main__":
    main()

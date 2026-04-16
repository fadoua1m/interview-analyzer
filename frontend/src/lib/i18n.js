import { createContext, createElement, useContext, useMemo, useState } from "react";

const I18nContext = createContext(null);

const MESSAGES = {
  en: {
    langEnglish: "English",
    langFrench: "French",
    sidebarMenu: "Menu",
    navDashboard: "Dashboard",
    navJobs: "Jobs",
    navInterviews: "Interviews",
    navSoftSkills: "Soft Skills",
    collapse: "Collapse",
    save: "Save",
    cancel: "Cancel",

    dashboardTitle: "Dashboard",
    totalJobs: "Total Jobs",
    seniorLead: "Senior / Lead",
    matchRate: "Match Rate",
    interviews: "Interviews",
    comingSoon: "Coming soon",
    recentJobs: "Recent Jobs",
    latestPositions: "Latest positions added",
    viewAll: "View all",
    noJobsYet: "No jobs yet",
    addFirstJob: "Add your first job",
    bySeniority: "By Seniority",
    distributionAcrossLevels: "Distribution across levels",
    noDataYet: "No data yet",
    moreAnalyticsSoon: "More analytics coming soon",

    jobsTitle: "Jobs",
    loading: "Loading...",
    addJob: "Add Job",
    positionsLabel: "positions",
    of: "of",
    searchTitleCompany: "Search title or company...",
    allLevels: "All levels",
    position: "Position",
    level: "Level",
    added: "Added",
    failedLoadJobs: "Failed to load jobs",
    checkConnection: "Check your connection and try again",
    noResultsFound: "No results found",
    adjustSearchFilter: "Try adjusting your search or filter",
    clearFilters: "Clear filters",

    interviewsTitle: "Interviews",
    newInterview: "New Interview",
    interviewCountLabel: "interviews",
    failedLoadInterviews: "Failed to load interviews.",
    noInterviewsYet: "No interviews yet",
    openJobCreateInterview: "Open a job and click \"Create Interview\"",

    softSkillsBank: "Soft Skills Bank",
    bilingualDefinitions: "Recruiters can manage bilingual competency definitions used by AI analysis.",
    addSoftSkill: "Add Soft Skill",
    keyPlaceholder: "Key (e.g. communication)",
    displayName: "Display name",
    descriptionClassifier: "Description used by AI classifier",
    active: "Active",
    inactive: "Inactive",
    add: "Add",
    showInactive: "Show inactive",
    loadingSoftSkills: "Loading soft skills...",
    noSoftSkillsFound: "No soft skills found for this language.",

    interviewSubmission: "Interview Submission",
    candidate: "Candidate",
    status: "Status",
    interview: "Interview",
    questions: "Questions",
    uploadInterviewVideo: "Upload your interview video",
    recordAllAnswers: "Record your answers to all listed questions and upload one video file.",
    processing: "Processing...",
    submit: "Submit",
    submissionClosed: "Submission is closed for this assignment.",
    processedResult: "Processed Result",
    decision: "Decision",
    overallScore: "Overall Score",
    processedDone: "Your interview has been processed.",
    invalidLink: "This candidate link is invalid or expired.",

    candidateFullReport: "Candidate Full Report",
    reportUnavailable: "Report is not available yet.",
    hiringDecision: "Hiring Decision",
    overallFitScore: "Overall Fit Score",
    interviewReference: "Interview Reference",
    questionsEvaluated: "Questions Evaluated",
    hrSummary: "HR Summary",
    visualSignals: "Visual Signals (Video)",
    contentSignals: "Content Signals (Text)",
    attention: "Attention",
    composure: "Composure",
    integrityRisk: "Integrity risk",
    keyObservations: "Key observations",
    relevanceScore: "Relevance score",
    softSkillsDetected: "Soft skills detected",
    softSkillsEvidence: "Soft Skills Evidence (Content)",
    candidatesSubmissions: "Candidates & Submissions",
    copyCandidateLink: "Copy Candidate Link",
    openLink: "Open link",
    openFullReport: "Open Full Report",
  },
  fr: {
    langEnglish: "Anglais",
    langFrench: "Francais",
    sidebarMenu: "Menu",
    navDashboard: "Tableau de bord",
    navJobs: "Postes",
    navInterviews: "Entretiens",
    navSoftSkills: "Soft skills",
    collapse: "Reduire",
    save: "Enregistrer",
    cancel: "Annuler",

    dashboardTitle: "Tableau de bord",
    totalJobs: "Total des postes",
    seniorLead: "Senior / Lead",
    matchRate: "Taux de correspondance",
    interviews: "Entretiens",
    comingSoon: "Bientot disponible",
    recentJobs: "Postes recents",
    latestPositions: "Derniers postes ajoutes",
    viewAll: "Voir tout",
    noJobsYet: "Aucun poste",
    addFirstJob: "Ajouter votre premier poste",
    bySeniority: "Par anciennete",
    distributionAcrossLevels: "Repartition par niveau",
    noDataYet: "Pas encore de donnees",
    moreAnalyticsSoon: "Plus d'analyses bientot",

    jobsTitle: "Postes",
    loading: "Chargement...",
    addJob: "Ajouter un poste",
    positionsLabel: "postes",
    of: "sur",
    searchTitleCompany: "Rechercher un titre ou une entreprise...",
    allLevels: "Tous les niveaux",
    position: "Poste",
    level: "Niveau",
    added: "Ajoute",
    failedLoadJobs: "Echec du chargement des postes",
    checkConnection: "Verifiez votre connexion et reessayez",
    noResultsFound: "Aucun resultat",
    adjustSearchFilter: "Ajustez la recherche ou le filtre",
    clearFilters: "Effacer les filtres",

    interviewsTitle: "Entretiens",
    newInterview: "Nouvel entretien",
    interviewCountLabel: "entretiens",
    failedLoadInterviews: "Echec du chargement des entretiens.",
    noInterviewsYet: "Aucun entretien",
    openJobCreateInterview: "Ouvrez un poste puis cliquez sur \"Creer un entretien\"",

    softSkillsBank: "Banque de soft skills",
    bilingualDefinitions: "Les recruteurs peuvent gerer des definitions bilingues utilisees par l'analyse IA.",
    addSoftSkill: "Ajouter une soft skill",
    keyPlaceholder: "Cle (ex: communication)",
    displayName: "Nom affiche",
    descriptionClassifier: "Description utilisee par le classifieur IA",
    active: "Actif",
    inactive: "Inactif",
    add: "Ajouter",
    showInactive: "Afficher inactifs",
    loadingSoftSkills: "Chargement des soft skills...",
    noSoftSkillsFound: "Aucune soft skill pour cette langue.",

    interviewSubmission: "Soumission d'entretien",
    candidate: "Candidat",
    status: "Statut",
    interview: "Entretien",
    questions: "Questions",
    uploadInterviewVideo: "Televerser votre video d'entretien",
    recordAllAnswers: "Enregistrez vos reponses a toutes les questions et televersez une seule video.",
    processing: "Traitement...",
    submit: "Soumettre",
    submissionClosed: "La soumission est fermee pour cette candidature.",
    processedResult: "Resultat traite",
    decision: "Decision",
    overallScore: "Score global",
    processedDone: "Votre entretien a ete traite.",
    invalidLink: "Ce lien candidat est invalide ou expire.",

    candidateFullReport: "Rapport complet du candidat",
    reportUnavailable: "Le rapport n'est pas encore disponible.",
    hiringDecision: "Decision de recrutement",
    overallFitScore: "Score global d'adequation",
    interviewReference: "Reference d'entretien",
    questionsEvaluated: "Questions evaluees",
    hrSummary: "Resume RH",
    visualSignals: "Signaux visuels (video)",
    contentSignals: "Signaux de contenu (texte)",
    attention: "Attention",
    composure: "Composture",
    integrityRisk: "Risque d'integrite",
    keyObservations: "Observations cles",
    relevanceScore: "Score de pertinence",
    softSkillsDetected: "Soft skills detectees",
    softSkillsEvidence: "Preuves de soft skills (contenu)",
    candidatesSubmissions: "Candidats et soumissions",
    copyCandidateLink: "Copier le lien candidat",
    openLink: "Ouvrir le lien",
    openFullReport: "Ouvrir le rapport complet",
  },
};

const VALUE_I18N_FR = {
  proceed: "A poursuivre",
  review: "A examiner",
  reject: "A rejeter",
  high: "Eleve",
  low: "Faible",
  moderate: "Modere",
  medium: "Moyen",
  reliable: "Fiable",
  unknown: "Inconnu",
  positive: "Positif",
  assigned: "Assigne",
  submitted: "Soumis",
  processed: "Traite",
  failed: "Echec",
};

function translateValueByLang(value, lang) {
  if (lang !== "fr") return value;
  const raw = String(value ?? "").trim();
  if (!raw) return value;
  const key = raw.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  return VALUE_I18N_FR[key] || value;
}

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem("app_lang") : null;
    if (stored === "en" || stored === "fr") return stored;
    const browser = typeof navigator !== "undefined" ? (navigator.language || "en").toLowerCase() : "en";
    return browser.startsWith("fr") ? "fr" : "en";
  });

  const value = useMemo(() => {
    const t = (key, fallback = "") => MESSAGES[lang]?.[key] || MESSAGES.en[key] || fallback || key;
    const setLanguage = (next) => {
      if (next !== "en" && next !== "fr") return;
      setLang(next);
      if (typeof window !== "undefined") {
        window.localStorage.setItem("app_lang", next);
      }
    };
    const tv = (input) => translateValueByLang(input, lang);
    return { lang, setLanguage, t, tv };
  }, [lang]);

  return createElement(I18nContext.Provider, { value }, children);
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}

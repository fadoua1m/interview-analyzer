// src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppLayout              from "./components/layout/AppLayout";
import Dashboard              from "./pages/Dashboard";
import JobsPage               from "./pages/jobs/JobsPage";
import InterviewsPage         from "./pages/interviews/InterviewsPage";
import InterviewDetail        from "./pages/interviews/InterviewDetail";
import CandidateReportPage    from "./pages/interviews/CandidateReportPage";
import SoftskillsPage         from "./pages/SoftskillsPage";
import CandidateSubmissionPage from "./pages/interviews/CandidateSubmissionPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/candidate/:token" element={<CandidateSubmissionPage />} />
        <Route
          path="*"
          element={
            <AppLayout>
              <Routes>
                <Route path="/"                                                             element={<Dashboard />}            />
                <Route path="/jobs"                                                         element={<JobsPage />}             />
                <Route path="/interviews"                                                   element={<InterviewsPage />}       />
                <Route path="/interviews/:id"                                               element={<InterviewDetail />}      />
                <Route path="/interviews/:interviewId/candidates/:candidateId/report"      element={<CandidateReportPage />}  />
                <Route path="/softskills"                                                   element={<SoftskillsPage />}       />
              </Routes>
            </AppLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import DataPage from "./pages/DataPage";
import TopologyPage from "./pages/TopologyPage";
import FitPage from "./pages/FitPage";
import ResultsPage from "./pages/ResultsPage";
import ScanPage from "./pages/ScanPage";
import ComparePage from "./pages/ComparePage";
import AcademyPage from "./pages/AcademyPage";
import LessonPage from "./pages/LessonPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="data" element={<DataPage />} />
        <Route path="topology" element={<TopologyPage />} />
        <Route path="fit" element={<FitPage />} />
        <Route path="results/:jobId" element={<ResultsPage />} />
        <Route path="scan/:parentId" element={<ScanPage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="compare/:parentId" element={<ComparePage />} />
        <Route path="academy" element={<AcademyPage />} />
        <Route path="academy/:lessonId" element={<LessonPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

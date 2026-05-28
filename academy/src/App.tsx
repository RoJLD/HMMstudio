import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import AcademyPage from "./pages/AcademyPage";
import LessonPage from "./pages/LessonPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/academy" replace />} />
        <Route path="academy" element={<AcademyPage />} />
        <Route path="academy/:lessonId" element={<LessonPage />} />
      </Route>
    </Routes>
  );
}

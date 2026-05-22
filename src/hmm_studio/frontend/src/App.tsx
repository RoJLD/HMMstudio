import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import TopologyPage from "./pages/TopologyPage";
import ResultsPage from "./pages/ResultsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="topology" element={<TopologyPage />} />
        <Route path="results/:jobId" element={<ResultsPage />} />
      </Route>
    </Routes>
  );
}

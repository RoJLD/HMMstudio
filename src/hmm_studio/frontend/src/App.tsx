import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import DataPage from "./pages/DataPage";
import TopologyPage from "./pages/TopologyPage";
import FitPage from "./pages/FitPage";
import ResultsPage from "./pages/ResultsPage";
import ScanPage from "./pages/ScanPage";

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
      </Route>
    </Routes>
  );
}

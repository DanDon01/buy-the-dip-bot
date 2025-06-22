import { BrowserRouter as Router, Route, Routes, Outlet } from "react-router-dom";
import StockDetailPage from "./pages/StockDetailPage";
import Layout from "./components/Layout";
import StockSidebar from "./components/StockSidebar";
import HomePage from "./pages/HomePage";
import BuyListPage from "./pages/BuyListPage";
import ScoringTuningPage from "./pages/ScoringTuningPage";
import './App.css';

const AppLayout = () => (
  <Layout sidebar={<StockSidebar />}>
    <Outlet />
  </Layout>
);

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="buylist" element={<BuyListPage />} />
          <Route path="scoring-tuning" element={<ScoringTuningPage />} />
          <Route path="stock/:ticker" element={<StockDetailPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;

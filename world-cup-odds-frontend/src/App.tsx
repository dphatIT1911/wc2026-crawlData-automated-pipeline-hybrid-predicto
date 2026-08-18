import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout/MainLayout';
import { Dashboard } from './pages/Dashboard/Dashboard';
import { Predictions } from './pages/Predictions/Predictions';
import { CrawlerData } from './pages/CrawlerData/CrawlerData';
import { Analytics } from './pages/Analytics/Analytics';
import { History } from './pages/History/History';
import { Settings } from './pages/Settings/Settings';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="predictions" element={<Predictions />} />
          <Route path="crawler" element={<CrawlerData />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="history" element={<History />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

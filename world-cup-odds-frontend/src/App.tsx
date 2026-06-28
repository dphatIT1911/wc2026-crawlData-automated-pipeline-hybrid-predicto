import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout/MainLayout';
import { Dashboard } from './pages/Dashboard/Dashboard';
import { Predictions } from './pages/Predictions/Predictions';
import { CrawlerData } from './pages/CrawlerData/CrawlerData';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="predictions" element={<Predictions />} />
          <Route path="crawler" element={<CrawlerData />} />
          <Route path="analytics" element={<div style={{padding: 'var(--spacing-xl)'}}>Analytics Module (Coming Soon)</div>} />
          <Route path="history" element={<div style={{padding: 'var(--spacing-xl)'}}>History Module (Coming Soon)</div>} />
          <Route path="settings" element={<div style={{padding: 'var(--spacing-xl)'}}>Settings Module (Coming Soon)</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../../components/Sidebar/Sidebar';
import { TopBar } from '../../components/TopBar/TopBar';
import './MainLayout.css';

export const MainLayout: React.FC = () => {
  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content-wrapper">
        <TopBar />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

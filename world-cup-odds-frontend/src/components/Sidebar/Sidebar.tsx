import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, BrainCircuit, Database, History, Settings, LineChart } from 'lucide-react';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">WC2026 AI</div>
      </div>
      
      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </NavLink>
        
        <NavLink to="/predictions" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <BrainCircuit size={20} />
          <span>AI Predictions</span>
        </NavLink>
        
        <NavLink to="/crawler" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Database size={20} />
          <span>Crawler Data</span>
        </NavLink>

        <NavLink to="/analytics" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LineChart size={20} />
          <span>Analytics</span>
        </NavLink>

        <NavLink to="/history" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <History size={20} />
          <span>History</span>
        </NavLink>
      </nav>
      
      <div className="sidebar-footer">
        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Settings size={20} />
          <span>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
};

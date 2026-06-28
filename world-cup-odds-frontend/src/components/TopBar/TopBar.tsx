import React from 'react';
import { Search, Bell, UserCircle } from 'lucide-react';
import './TopBar.css';
import { Button } from '../Button/Button';

export const TopBar: React.FC = () => {
  return (
    <header className="top-bar">
      <div className="search-container">
        <Search className="search-icon" size={18} />
        <input 
          type="text" 
          className="search-input" 
          placeholder="Search matches, teams, or predictions... (Ctrl+K)" 
        />
      </div>
      
      <div className="top-bar-actions">
        <Button variant="tertiary-text" className="icon-btn">
          <Bell size={20} />
        </Button>
        <Button variant="tertiary-text" className="icon-btn">
          <UserCircle size={24} />
        </Button>
      </div>
    </header>
  );
};

import React, { useEffect, useState } from 'react';
import Navbar from './components/Common/Navbar';
import Disclaimer from './components/Common/Disclaimer';
import Loader from './components/Common/Loader';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CaseSelection from './pages/CaseSelection';
import Briefing from './pages/Briefing';
import Simulation from './pages/Simulation';
import Results from './pages/Results';
import { api } from './api/client';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Theme State (light/dark)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('diagnos_theme') || 'light';
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('diagnos_theme', theme);
  }, [theme]);

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Navigation Routing States
  const [activePage, setActivePage] = useState('landing'); // landing, login, register, dashboard, cases, briefing, simulation, results
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);

  // Authenticate user on mount
  useEffect(() => {
    async function loadUser() {
      try {
        const u = await api.getMe();
        if (u) {
          setUser(u);
          setActivePage('dashboard');
        }
      } catch (err) {
        console.error('Initial user loading failed:', err);
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, []);

  const handleLoginSuccess = (authenticatedUser) => {
    setUser(authenticatedUser);
    setActivePage('dashboard');
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setActivePage('landing');
  };

  const handleNavigate = (page) => {
    setActivePage(page);
  };

  const handleSelectCase = (caseId) => {
    setSelectedCaseId(caseId);
    setActivePage('briefing');
  };

  const handleStartSimulation = (sessionId) => {
    setActiveSessionId(sessionId);
    setActivePage('simulation');
  };

  const handleSimulationComplete = (sessionId) => {
    setActiveSessionId(sessionId);
    setActivePage('results');
  };

  const handleSelectSession = (sessionId, status) => {
    setActiveSessionId(sessionId);
    if (status === 'completed') {
      setActivePage('results');
    } else {
      setActivePage('simulation');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center">
        <Loader size="large" text="Starting DiagnOS Workspace Simulator..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 transition-colors">
      {/* Navigation and Disclaimer Headers */}
      <Navbar 
        user={user} 
        activePage={activePage} 
        onNavigate={handleNavigate} 
        onLogout={handleLogout} 
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />
      <Disclaimer />

      {/* Main Pages Content Switcher */}
      <main className="flex-1">
        {activePage === 'landing' && (
          <Landing onNavigate={handleNavigate} />
        )}
        
        {activePage === 'login' && (
          <Login 
            isRegisterInitial={false} 
            onLoginSuccess={handleLoginSuccess} 
            onNavigate={handleNavigate} 
          />
        )}
        
        {activePage === 'register' && (
          <Login 
            isRegisterInitial={true} 
            onLoginSuccess={handleLoginSuccess} 
            onNavigate={handleNavigate} 
          />
        )}

        {/* Authenticated routes */}
        {user && activePage === 'dashboard' && (
          <Dashboard 
            user={user} 
            onNavigate={handleNavigate} 
            onSelectSession={handleSelectSession} 
          />
        )}

        {user && activePage === 'cases' && (
          <CaseSelection 
            onNavigate={handleNavigate} 
            onSelectCase={handleSelectCase} 
          />
        )}

        {user && activePage === 'briefing' && (
          <Briefing 
            caseId={selectedCaseId} 
            onStartSimulation={handleStartSimulation} 
            onNavigate={handleNavigate} 
          />
        )}

        {user && activePage === 'simulation' && (
          <Simulation 
            sessionId={activeSessionId} 
            onNavigate={handleNavigate} 
            onSimulationComplete={handleSimulationComplete} 
          />
        )}

        {user && activePage === 'results' && (
          <Results 
            sessionId={activeSessionId} 
            onNavigate={handleNavigate} 
          />
        )}
      </main>
    </div>
  );
}

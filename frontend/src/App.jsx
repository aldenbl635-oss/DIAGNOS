import React, { useEffect, useState } from 'react';
import Navbar from './components/Common/Navbar';
import Disclaimer from './components/Common/Disclaimer';
import Loader from './components/Common/Loader';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import EncounterSetup from './pages/EncounterSetup';
import PatientEncounter from './pages/PatientEncounter';
import Results from './pages/Results';
import DataSources from './pages/DataSources';
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

  // Navigation Routing States: landing, login, register, dashboard, encounter-setup, simulation, results
  const [activePage, setActivePage] = useState('landing');
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

  // Listen to global 401 unauthorized events to force logout clean-up
  useEffect(() => {
    const handleUnauthorized = () => {
      handleLogout();
    };
    window.addEventListener('diagnos-unauthorized', handleUnauthorized);
    return () => window.removeEventListener('diagnos-unauthorized', handleUnauthorized);
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
    // Map legacy page routes if any
    if (page === 'cases' || page === 'briefing') {
      setActivePage('encounter-setup');
    } else {
      setActivePage(page);
    }
  };

  const handleStartEncounter = (sessionId) => {
    setActiveSessionId(sessionId);
    setActivePage('simulation');
  };

  const handleEncounterComplete = (sessionId) => {
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
      <div className="min-h-screen bg-slate-900 flex flex-col justify-center items-center">
        <Loader size="large" text="Starting DiagnOS Virtual Patient Lab..." />
      </div>
    );
  }

  // Determine if full-screen encounter mode is active (hides top navigation chrome for maximum immersion)
  const isEncounterMode = activePage === 'simulation' || activePage === 'encounter-setup';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 transition-colors">
      {/* Navigation and Disclaimer Headers (Hidden in full-screen patient encounter mode) */}
      {!isEncounterMode && (
        <>
          <Navbar
            user={user}
            activePage={activePage}
            onNavigate={handleNavigate}
            onLogout={handleLogout}
            theme={theme}
            onToggleTheme={handleToggleTheme}
          />
          <Disclaimer />
        </>
      )}

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

        {user && (activePage === 'encounter-setup' || activePage === 'cases' || activePage === 'briefing') && (
          <EncounterSetup
            onStartEncounter={handleStartEncounter}
            onNavigate={handleNavigate}
          />
        )}

        {user && activePage === 'simulation' && (
          <PatientEncounter
            sessionId={activeSessionId}
            onNavigate={handleNavigate}
            onEncounterComplete={handleEncounterComplete}
          />
        )}

        {user && activePage === 'results' && (
          <Results
            sessionId={activeSessionId}
            onNavigate={handleNavigate}
          />
        )}

        {user && activePage === 'sources' && (
          <DataSources
            onNavigate={handleNavigate}
          />
        )}
      </main>
    </div>
  );
}

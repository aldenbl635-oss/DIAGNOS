import React from 'react';
import { HeartPulse, LogOut, BookOpen, LayoutDashboard, Sun, Moon } from 'lucide-react';

export default function Navbar({ user, activePage, onNavigate, onLogout, theme, onToggleTheme }) {
  return (
    <nav className="bg-white border-b border-slate-200/80 sticky top-0 z-50 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center gap-8">
            {/* Logo */}
            <div
              className="flex items-center gap-2.5 cursor-pointer"
              onClick={() => user ? onNavigate('dashboard') : onNavigate('landing')}
              id="nav-logo"
            >
              <div className="bg-medical-500 text-white p-2 rounded-xl shadow-md shadow-medical-100">
                <HeartPulse className="w-5 h-5" />
              </div>
              <span className="font-sans font-extrabold text-xl tracking-tight text-slate-900">
                Diagn<span className="text-medical-600">OS</span>
              </span>
            </div>

            {/* Main Nav Items */}
            {user && (
              <div className="hidden md:flex items-center gap-1">
                <button
                  id="nav-btn-dashboard"
                  onClick={() => onNavigate('dashboard')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${activePage === 'dashboard'
                      ? 'bg-slate-100 text-slate-900'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Virtual Patient Lab
                </button>
                <button
                  id="nav-btn-encounter"
                  onClick={() => onNavigate('encounter-setup')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${activePage === 'encounter-setup' || activePage === 'simulation'
                      ? 'bg-slate-100 text-slate-900'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                >
                  <HeartPulse className="w-4 h-4 text-medical-600" />
                  New Encounter
                </button>
                <button
                  id="nav-btn-sources"
                  onClick={() => onNavigate('sources')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${activePage === 'sources'
                      ? 'bg-slate-100 text-slate-900'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                >
                  <BookOpen className="w-4 h-4 text-emerald-600" />
                  Data Sources
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle Button */}
            <button
              id="theme-toggle-btn"
              type="button"
              onClick={onToggleTheme}
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              className="p-2.5 rounded-xl border border-slate-200/80 bg-slate-50 hover:bg-slate-100 text-slate-600 transition-all duration-200 flex items-center justify-center gap-1.5"
            >
              {theme === 'dark' ? (
                <>
                  <Sun className="w-4 h-4 text-amber-400 animate-fade-in" />
                  <span className="text-xs font-semibold hidden md:inline text-amber-400">Light</span>
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4 text-slate-600 animate-fade-in" />
                  <span className="text-xs font-semibold hidden md:inline text-slate-600">Dark</span>
                </>
              )}
            </button>

            {user ? (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200/80 rounded-lg">
                  <div className="w-6 h-6 rounded-full bg-medical-100 text-medical-700 flex items-center justify-center font-bold text-xs uppercase">
                    {user.name ? user.name[0] : 'U'}
                  </div>
                  <span className="text-sm font-semibold text-slate-700 hidden sm:inline">{user.name}</span>
                </div>
                <button
                  id="nav-btn-logout"
                  onClick={onLogout}
                  className="flex items-center justify-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 rounded-lg transition-all duration-200"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  id="nav-btn-login"
                  onClick={() => onNavigate('login')}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-50 rounded-lg transition-all duration-200"
                >
                  Login
                </button>
                <button
                  id="nav-btn-register"
                  onClick={() => onNavigate('register')}
                  className="px-4 py-2 text-sm font-semibold text-white bg-medical-500 hover:bg-medical-700 rounded-lg shadow-sm shadow-medical-100 transition-all duration-200"
                >
                  Sign Up
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}


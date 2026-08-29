import React, { useState } from 'react';
import { HeartPulse, Key, Mail, User, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';

export default function Login({ isRegisterInitial = false, onLoginSuccess, onNavigate }) {
  const [isRegister, setIsRegister] = useState(isRegisterInitial);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [specialization, setSpecialization] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let user;
      if (isRegister) {
        if (!specialization) {
          setError('Please select a specialization.');
          setLoading(false);
          return;
        }
        user = await api.register(name, email, password, specialization);
      } else {
        user = await api.login(email, password);
      }
      onLoginSuccess(user);
    } catch (err) {
      setError(err.message || 'An error occurred during authentication.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoAccess = async () => {
    setError(null);
    setLoading(true);
    // Automatically register/login a guest user
    const guestEmail = `guest_${Math.floor(Math.random() * 100000)}@diagnos.org`;
    const guestPassword = 'password123';
    const guestName = 'Alex';

    try {
      // Try registering first
      const user = await api.register(guestName, guestEmail, guestPassword);
      onLoginSuccess(user);
    } catch (err) {
      // If register failed, try login (should not fail for random guest email)
      try {
        const user = await api.login(guestEmail, guestPassword);
        onLoginSuccess(user);
      } catch (innerErr) {
        setError('Failed to configure Demo/Guest access. Please try standard registration.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
      <div className="max-w-md w-full space-y-8 bg-white p-8 border border-slate-200/80 rounded-2xl shadow-xl shadow-slate-100 animate-slide-up">

        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex bg-medical-50 text-medical-600 p-2.5 rounded-xl border border-medical-100/50 mb-2">
            <HeartPulse className="w-6 h-6 animate-pulse-slow" />
          </div>
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            {isRegister ? 'Create your account' : 'Sign in to DiagnOS'}
          </h2>
          <p className="text-xs text-slate-500 max-w-xs mx-auto">
            Access the clinical reasoning workstation simulation for medical education.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-100 rounded-xl p-3 flex items-start gap-2.5 text-xs text-red-700">
            <AlertCircle className="w-4.5 h-4.5 text-red-500 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          {isRegister && (
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700" htmlFor="reg-name">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
                <input
                  id="reg-name"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Alex Mercer"
                  className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 transition-all"
                />
              </div>
            </div>
          )}

          {isRegister && (
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700" htmlFor="reg-specialization">Specialization</label>
              <div className="relative">
                <ShieldCheck className="absolute left-3 top-3 w-4 h-4 text-slate-400 pointer-events-none" />
                <select
                  id="reg-specialization"
                  required
                  value={specialization}
                  onChange={(e) => setSpecialization(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 transition-all appearance-none"
                >
                  <option value="" disabled>Select Specialization ▼</option>
                  <option value="Cardiology">Cardiology</option>
                  <option value="Gastroenterology">Gastroenterology</option>
                  <option value="Neurology">Neurology</option>
                  <option value="Psychiatry">Psychiatry</option>
                  <option value="General Surgery">General Surgery</option>
                  <option value="Pulmonology">Pulmonology</option>
                  <option value="Urology">Urology</option>
                  <option value="Vascular Medicine">Vascular Medicine</option>
                  <option value="Emergency Medicine">Emergency Medicine (General)</option>
                </select>
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700" htmlFor="login-email">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alex@medschool.edu"
                className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 transition-all"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700" htmlFor="login-password">Password</label>
            <div className="relative">
              <Key className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
              <input
                id="login-password"
                type="password"
                required
                minLength={isRegister ? 6 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isRegister ? "Minimum 6 characters" : "••••••••"}
                className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 transition-all"
              />
            </div>
          </div>

          <button
            id="auth-submit-btn"
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-medical-500 hover:bg-medical-700 disabled:bg-slate-300 rounded-lg shadow-md shadow-medical-100 flex items-center justify-center gap-2 transition-all duration-200"
          >
            {loading ? 'Authenticating...' : isRegister ? 'Create Account' : 'Sign In'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Divider */}
        <div className="relative flex items-center justify-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <span className="relative px-3 bg-white text-[10px] font-bold text-slate-400 uppercase tracking-widest">OR</span>
        </div>

        {/* Demo login CTA */}
        <div className="space-y-3">
          <button
            id="auth-demo-btn"
            type="button"
            onClick={handleDemoAccess}
            disabled={loading}
            className="w-full py-2.5 px-4 text-sm font-semibold text-medical-700 bg-medical-50 hover:bg-medical-100 border border-medical-200/60 rounded-lg flex items-center justify-center gap-2 transition-all duration-200"
          >
            <ShieldCheck className="w-4 h-4 text-medical-600" />
            Instant Guest / Demo Access
          </button>

          {/* Toggle link */}
          <div className="text-center">
            <button
              id="auth-toggle-state"
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError(null);
              }}
              className="text-xs font-semibold text-slate-500 hover:text-medical-600 transition-colors"
            >
              {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

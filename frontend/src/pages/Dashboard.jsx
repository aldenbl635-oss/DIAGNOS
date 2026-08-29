import React, { useEffect, useState } from 'react';
import {
  Flame,
  Award,
  Activity,
  History,
  TrendingUp,
  AlertCircle,
  Play,
  CheckCircle,
  Clock,
  ArrowRight,
  HeartPulse,
  UserCheck,
  ShieldCheck
} from 'lucide-react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar } from 'recharts';

export default function Dashboard({ user: initialUser, onNavigate, onSelectSession }) {
  const [user, setUser] = useState(initialUser);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [updatingSpec, setUpdatingSpec] = useState(false);
  const [specInput, setSpecInput] = useState('');

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await api.getDashboard();
        setStats(data);
      } catch (err) {
        setError(err.message || 'Failed to fetch encounter data.');
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  const getGreeting = () => {
    const hr = new Date().getHours();
    if (hr < 12) return 'Good morning';
    if (hr < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const handleUpdateSpecialization = async () => {
    if (!specInput) return;
    setUpdatingSpec(true);
    try {
      const updatedUser = await api.updateSpecialization(specInput);
      setUser(updatedUser);
    } catch (err) {
      alert(err.message || 'Failed to update specialization');
    } finally {
      setUpdatingSpec(false);
    }
  };

  if (loading) return <Loader text="Connecting to Virtual Patient Lab..." />;
  if (error) return (
    <div className="max-w-md mx-auto my-12 p-6 bg-red-50 border border-red-100 rounded-xl text-center space-y-4">
      <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
      <h3 className="font-bold text-red-800">Connection Error</h3>
      <p className="text-sm text-red-600">{error}</p>
      <button onClick={() => window.location.reload()} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold">
        Retry Connection
      </button>
    </div>
  );

  const chartData = Object.entries(stats.category_scores).map(([name, score]) => ({
    subject: name,
    score: score,
    fullMark: 100,
  }));

  const hasSimulations = stats.cases_completed > 0 || stats.recent_simulations.length > 0;
  const activeSession = stats.recent_simulations.find(s => s.status === 'in_progress');

  if (!user.specialization) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
        <div className="max-w-md w-full space-y-8 bg-white p-8 border border-slate-200/80 rounded-2xl shadow-xl shadow-slate-100 animate-slide-up text-center">
          <ShieldCheck className="w-12 h-12 text-medical-600 mx-auto" />
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">Select your specialization</h2>
          <p className="text-sm text-slate-500">Please choose a medical specialization to see relevant cases before you access the dashboard.</p>
          <div className="space-y-4 text-left">
            <select
              value={specInput}
              onChange={(e) => setSpecInput(e.target.value)}
              className="w-full px-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 appearance-none"
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
            <button
              onClick={handleUpdateSpecialization}
              disabled={updatingSpec || !specInput}
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-medical-500 hover:bg-medical-700 disabled:bg-slate-300 rounded-lg transition-all"
            >
              {updatingSpec ? 'Saving...' : 'Continue'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">

      {/* ─── Hero Header ─── */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-teal-950 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-2 z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs font-bold uppercase tracking-wider">
            <HeartPulse className="w-3.5 h-3.5 animate-pulse" />
            Virtual Patient Lab
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs font-bold uppercase tracking-wider ml-2">
            <UserCheck className="w-3.5 h-3.5" />
            Specialization: {user.specialization}
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            {getGreeting()}, Dr. {user.name?.split(' ')[0] || user.name}.
          </h1>
          <p className="text-sm sm:text-base text-slate-300 font-normal leading-relaxed">
            Practice clinical reasoning through realistic patient encounters.
          </p>
        </div>

        {/* Action CTAs */}
        <div className="flex flex-col sm:flex-row gap-3 z-10 w-full md:w-auto">
          <button
            id="dash-btn-start-encounter"
            onClick={() => onNavigate('encounter-setup')}
            className="flex items-center justify-center gap-2.5 px-7 py-3.5 bg-gradient-to-r from-teal-500 to-medical-600 hover:from-teal-400 hover:to-medical-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-teal-500/20 transition-all duration-200"
          >
            <Play className="w-4 h-4 fill-current" />
            Start New Patient Encounter
          </button>

          {activeSession && (
            <button
              id="dash-btn-continue-encounter"
              onClick={() => onSelectSession(activeSession.session_id, activeSession.status)}
              className="flex items-center justify-center gap-2 px-5 py-3.5 bg-white/10 hover:bg-white/20 text-white border border-white/10 font-semibold text-sm rounded-xl transition-all duration-200"
            >
              Continue Encounter
            </button>
          )}
        </div>
      </div>

      {/* ─── Practice Guidance / Adaptive Feedback ─── */}
      {stats.recommendation && (
        <div className="bg-teal-50/60 border border-teal-100 rounded-2xl p-4 flex gap-3.5 items-start">
          <div className="p-2 bg-white rounded-lg border border-teal-200 shadow-sm shrink-0">
            <Activity className="w-5 h-5 text-teal-600 animate-pulse-slow" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-teal-900">Clinical Focus Guidance</h4>
            <p className="text-xs text-teal-800 font-medium leading-relaxed">{stats.recommendation}</p>
          </div>
        </div>
      )}

      {/* ─── Performance Summary Cards ─── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Encounters Completed</span>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{stats.cases_completed}</span>
            <span className="text-xs font-semibold text-slate-400">patients</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
            <div className="bg-teal-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, stats.cases_completed * 10)}%` }} />
          </div>
        </div>

        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Average Reasoning Score</span>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-900">{stats.average_score}</span>
            <span className="text-sm font-bold text-slate-400">/ 100</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
            <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${stats.average_score}%` }} />
          </div>
        </div>

        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Highest Encounter Score</span>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-900">{stats.best_score}</span>
            <span className="text-sm font-bold text-slate-400">/ 100</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
            <div className="bg-medical-500 h-1.5 rounded-full" style={{ width: `${stats.best_score}%` }} />
          </div>
        </div>

        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Clinical Practice Streak</span>
          <div className="flex items-center gap-2">
            <Flame className={`w-7 h-7 ${stats.streak > 0 ? 'text-amber-500 fill-amber-500' : 'text-slate-300'}`} />
            <span className="text-3xl font-extrabold text-slate-900">{stats.streak}</span>
            <span className="text-xs font-semibold text-slate-400">days</span>
          </div>
          <div className="text-[10px] font-bold text-slate-400 tracking-wider">
            {stats.streak > 0 ? 'Keep practicing daily!' : 'Complete an encounter to start'}
          </div>
        </div>
      </div>

      {/* ─── Main Content Grid: Competencies & Encounters ─── */}
      <div className="grid lg:grid-cols-12 gap-8">

        {/* Radar Competency Chart */}
        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm lg:col-span-7 flex flex-col">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-teal-600" />
              <h3 className="font-bold text-slate-800">Clinical Competency Profile</h3>
            </div>
            <span className="text-xs font-semibold text-slate-400">Evaluated across encounters</span>
          </div>

          <div className="flex-1 min-h-[300px] flex items-center justify-center pt-4">
            {hasSimulations ? (
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 10, fontWeight: 600 }} />
                  <Radar name="Student score" dataKey="score" stroke="#0d9488" fill="#0d9488" fillOpacity={0.25} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center p-8 space-y-3">
                <TrendingUp className="w-12 h-12 text-slate-300 mx-auto" />
                <h4 className="font-bold text-slate-700">No competency data yet</h4>
                <p className="text-xs text-slate-400 max-w-xs mx-auto">
                  Complete your first virtual patient encounter to view your clinical competency profile.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Encounters List */}
        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm lg:col-span-5 flex flex-col">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-teal-600" />
              <h3 className="font-bold text-slate-800">Recent Encounters</h3>
            </div>
            <span className="text-xs font-semibold text-slate-400">History</span>
          </div>

          <div className="flex-1 overflow-y-auto max-h-[320px] space-y-3">
            {stats.recent_simulations.length > 0 ? (
              stats.recent_simulations.map((sim) => (
                <div
                  key={sim.session_id}
                  onClick={() => onSelectSession(sim.session_id, sim.status)}
                  className="p-3.5 border border-slate-100 hover:border-teal-200 hover:bg-teal-50/20 rounded-xl cursor-pointer transition-all duration-200 flex justify-between items-center group"
                >
                  <div className="space-y-1">
                    <h4 className="text-sm font-bold text-slate-800 group-hover:text-teal-700 transition-colors">
                      Patient Encounter — Emergency
                    </h4>
                    <div className="flex items-center gap-2 text-[10px] font-semibold text-slate-400">
                      <span>{sim.specialty}</span>
                      <span>•</span>
                      <span>{sim.difficulty}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {sim.status === 'completed' ? (
                      <div className="flex flex-col items-end">
                        <span className="text-sm font-extrabold text-slate-800">{sim.score}</span>
                        <span className="text-[9px] font-bold text-emerald-600 flex items-center gap-0.5">
                          <CheckCircle className="w-2.5 h-2.5" /> Graded
                        </span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-end">
                        <span className="text-[10px] font-semibold text-slate-400 italic">In Progress</span>
                        <span className="text-[9px] font-bold text-amber-600 flex items-center gap-0.5">
                          <Clock className="w-2.5 h-2.5" /> Resume
                        </span>
                      </div>
                    )}
                    <ArrowRight className="w-4 h-4 text-slate-350 group-hover:text-teal-600 transition-colors" />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 space-y-3">
                <UserCheck className="w-12 h-12 text-slate-300 mx-auto" />
                <h4 className="font-bold text-slate-700">No encounters yet</h4>
                <p className="text-xs text-slate-400 max-w-xs mx-auto">
                  You haven't conducted any patient encounters yet. Start your first encounter to evaluate a virtual patient.
                </p>
                <button
                  id="dash-btn-empty-start"
                  onClick={() => onNavigate('encounter-setup')}
                  className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold shadow-sm transition-colors"
                >
                  Start New Patient Encounter
                </button>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

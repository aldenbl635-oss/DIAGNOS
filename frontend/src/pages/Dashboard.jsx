import React, { useEffect, useState } from 'react';
import { 
  BookOpen, 
  Flame, 
  Award, 
  Activity, 
  History,
  TrendingUp,
  AlertCircle,
  Play,
  CheckCircle,
  Clock,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function Dashboard({ user, onNavigate, onSelectSession }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await api.getDashboard();
        setStats(data);
      } catch (err) {
        setError(err.message || 'Failed to fetch dashboard data.');
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

  if (loading) return <Loader text="Loading clinical performance metrics..." />;
  if (error) return (
    <div className="max-w-md mx-auto my-12 p-6 bg-red-50 border border-red-100 rounded-xl text-center space-y-4">
      <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
      <h3 className="font-bold text-red-800">Dashboard Error</h3>
      <p className="text-sm text-red-600">{error}</p>
      <button onClick={() => window.location.reload()} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold">
        Retry
      </button>
    </div>
  );

  // Convert category scores object into array format for Recharts
  const chartData = Object.entries(stats.category_scores).map(([name, score]) => ({
    subject: name,
    score: score,
    fullMark: 100,
  }));

  const hasSimulations = stats.cases_completed > 0 || stats.recent_simulations.length > 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Welcome header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200/60 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {getGreeting()}, {user.name}.
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">
            Track your diagnostic skill progression and complete clinical scenarios.
          </p>
        </div>
        <button
          id="dash-btn-start"
          onClick={() => onNavigate('cases')}
          className="flex items-center gap-2 px-5 py-2.5 bg-medical-500 hover:bg-medical-700 text-white font-semibold rounded-xl shadow-md shadow-medical-100 transition-all duration-200"
        >
          <Play className="w-4 h-4 fill-current" />
          Start New Simulation
        </button>
      </div>

      {/* Adaptive Learning recommendation box */}
      {stats.recommendation && (
        <div className="bg-medical-50/60 border border-medical-100 rounded-2xl p-4 flex gap-3.5 items-start">
          <div className="p-2 bg-white rounded-lg border border-medical-200 shadow-sm shrink-0">
            <Activity className="w-5 h-5 text-medical-600 animate-pulse-slow" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-medical-900">Recommended Practice Guidance</h4>
            <p className="text-xs text-medical-700 font-medium leading-relaxed">{stats.recommendation}</p>
          </div>
        </div>
      )}

      {/* Stats Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Simulations Completed</span>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{stats.cases_completed}</span>
            <span className="text-xs font-semibold text-slate-400">cases</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
            <div className="bg-medical-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, stats.cases_completed * 10)}%` }} />
          </div>
        </div>

        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Average Reasoning</span>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-900">{stats.average_score}</span>
            <span className="text-sm font-bold text-slate-400">/ 100</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
            <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${stats.average_score}%` }} />
          </div>
        </div>

        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Personal Best Score</span>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-900">{stats.best_score}</span>
            <span className="text-sm font-bold text-slate-400">/ 100</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
            <div className="bg-teal-500 h-1.5 rounded-full" style={{ width: `${stats.best_score}%` }} />
          </div>
        </div>

        <div className="bg-white border border-slate-200/80 p-5 rounded-2xl shadow-sm flex flex-col justify-between space-y-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Current Streak</span>
          <div className="flex items-center gap-2">
            <Flame className={`w-7 h-7 ${stats.streak > 0 ? 'text-amber-500 fill-amber-500' : 'text-slate-300'}`} />
            <span className="text-3xl font-extrabold text-slate-900">{stats.streak}</span>
            <span className="text-xs font-semibold text-slate-400">days</span>
          </div>
          <div className="text-[10px] font-bold text-slate-400 tracking-wider">
            {stats.streak > 0 ? 'Keep it burning!' : 'Complete a case to start a streak'}
          </div>
        </div>
      </div>

      {/* Main Grid: Charts & Recents */}
      <div className="grid lg:grid-cols-12 gap-8">
        
        {/* Chart Column */}
        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm lg:col-span-7 flex flex-col">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-medical-600" />
              <h3 className="font-bold text-slate-800">Skill Competency Radar</h3>
            </div>
            <span className="text-xs font-semibold text-slate-400">Values graded 0-100</span>
          </div>
          
          <div className="flex-1 min-h-[300px] flex items-center justify-center pt-4">
            {hasSimulations ? (
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 10, fontWeight: 600 }} />
                  <Radar name="Student score" dataKey="score" stroke="#0284c7" fill="#0284c7" fillOpacity={0.25} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center p-8 space-y-3">
                <TrendingUp className="w-12 h-12 text-slate-300 mx-auto" />
                <h4 className="font-bold text-slate-700">No competency data yet</h4>
                <p className="text-xs text-slate-400 max-w-xs mx-auto">
                  Complete your first clinical simulation to view your personalized diagnostics radar.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Recents Column */}
        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm lg:col-span-5 flex flex-col">
          <div className="flex items-center gap-2 pb-4 border-b border-slate-100 mb-4">
            <History className="w-5 h-5 text-medical-600" />
            <h3 className="font-bold text-slate-800">Recent Simulations</h3>
          </div>

          <div className="flex-1 overflow-y-auto max-h-[320px] space-y-3">
            {stats.recent_simulations.length > 0 ? (
              stats.recent_simulations.map((sim) => (
                <div 
                  key={sim.session_id}
                  onClick={() => onSelectSession(sim.session_id, sim.status)}
                  className="p-3.5 border border-slate-100 hover:border-medical-200 hover:bg-medical-50/20 rounded-xl cursor-pointer transition-all duration-200 flex justify-between items-center group"
                >
                  <div className="space-y-1">
                    <h4 className="text-sm font-bold text-slate-800 group-hover:text-medical-700 transition-colors">
                      {sim.title}
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
                    <ArrowRight className="w-4 h-4 text-slate-350 group-hover:text-medical-600 transition-colors" />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 space-y-3">
                <BookOpen className="w-12 h-12 text-slate-300 mx-auto" />
                <h4 className="font-bold text-slate-700">No recent sessions</h4>
                <p className="text-xs text-slate-400 max-w-xs mx-auto">
                  You haven't run any clinical workstations yet. Go to the Case Library to get started.
                </p>
                <button
                  id="dash-btn-library-empty"
                  onClick={() => onNavigate('cases')}
                  className="px-4 py-2 border border-slate-200 hover:border-slate-300 rounded-lg text-xs font-bold text-slate-650 hover:bg-slate-50 transition-colors"
                >
                  View Case Library
                </button>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

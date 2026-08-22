import React, { useEffect, useState } from 'react';
import { BookOpen, Clock, BarChart, CheckCircle, ShieldAlert, Lock, Play } from 'lucide-react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';

export default function CaseSelection({ onNavigate, onSelectCase }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchCases() {
      try {
        const data = await api.getCases();
        setCases(data);
      } catch (err) {
        setError('Failed to load clinical library.');
      } finally {
        setLoading(false);
      }
    }
    fetchCases();
  }, []);

  const placeholders = [
    {
      id: "stroke_002",
      title: "Sudden Neurological Deficit",
      specialty: "Emergency Medicine / Neurology",
      difficulty: "Advanced",
      duration_mins: 25,
      skills: ["Neurological grading", "Stroke protocols", "CT scan sequencing"],
      isLocked: true
    },
    {
      id: "abdomen_003",
      title: "Acute Abdominal Pain",
      specialty: "Emergency Medicine / General Surgery",
      difficulty: "Intermediate",
      duration_mins: 20,
      skills: ["Surgical vs medical sorting", "Focused ultrasound", "Risk scoring"],
      isLocked: true
    },
    {
      id: "dyspnea_004",
      title: "Shortness of Breath",
      specialty: "Emergency Medicine / Pulmonology",
      difficulty: "Intermediate",
      duration_mins: 15,
      skills: ["Airway stabilization", "ABG interpretation", "Pathology sequencing"],
      isLocked: true
    }
  ];

  if (loading) return <Loader text="Loading clinical library..." />;

  // Group all cases (real from backend + placeholders)
  const activeCasesIds = cases.map(c => c.id);
  const allCases = [
    ...cases.map(c => ({
      ...c,
      skills: ["History taking", "Cardiac risk assessment", "Investigation prioritization", "Evidence interpretation"],
      isLocked: false
    })),
    ...placeholders.filter(p => !activeCasesIds.includes(p.id))
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      <div className="border-b border-slate-200/60 pb-6">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Clinical Case Library</h1>
        <p className="text-sm text-slate-500 font-medium mt-1">
          Select a case to begin your diagnostic assessment. Try the active demo case: <strong>Atypical Chest Pain</strong>.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {allCases.map((c) => (
          <div 
            key={c.id}
            className={`bg-white border rounded-2xl p-6 flex flex-col justify-between space-y-5 transition-all duration-200 ${
              c.isLocked 
                ? 'opacity-65 border-slate-200 bg-slate-50/50' 
                : 'border-slate-200 hover:border-medical-300 hover:shadow-lg hover:shadow-slate-100 cursor-pointer'
            }`}
            onClick={() => !c.isLocked && onSelectCase(c.id)}
          >
            {/* Card Top */}
            <div className="space-y-3.5">
              <div className="flex justify-between items-start gap-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-100 px-2.5 py-1 rounded-md">
                  {c.specialty}
                </span>
                
                {c.isLocked ? (
                  <span className="text-[9px] font-bold text-slate-500 bg-slate-200/80 px-2 py-0.5 rounded flex items-center gap-1 uppercase tracking-wide">
                    <Lock className="w-2.5 h-2.5" /> Locked
                  </span>
                ) : (
                  <span className="text-[9px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded flex items-center gap-1 uppercase tracking-wide animate-pulse-slow">
                    ● Active Demo
                  </span>
                )}
              </div>

              <div>
                <h3 className="text-xl font-bold text-slate-900 leading-snug">{c.title}</h3>
                {c.chief_complaint && (
                  <p className="text-xs text-slate-500 font-semibold mt-1">Chief Complaint: "{c.chief_complaint}"</p>
                )}
              </div>

              {/* Badges details */}
              <div className="flex gap-4 text-xs font-semibold text-slate-500 pt-1">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-slate-450" /> {c.duration_mins} mins
                </span>
                <span className="flex items-center gap-1.5">
                  <BarChart className="w-4 h-4 text-slate-450" /> {c.difficulty}
                </span>
              </div>
            </div>

            {/* Card Middle: Skills list */}
            <div className="border-t border-slate-100 pt-4">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2">Skills Tested:</span>
              <div className="flex flex-wrap gap-1.5">
                {c.skills.map((skill, idx) => (
                  <span key={idx} className="bg-slate-100/70 border border-slate-200/40 text-[10px] text-slate-600 font-bold px-2 py-0.5 rounded">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            {/* Card Bottom: Button */}
            <div className="pt-2">
              {c.isLocked ? (
                <button
                  disabled
                  className="w-full py-2.5 bg-slate-200 text-slate-400 font-semibold text-sm rounded-xl cursor-not-allowed flex items-center justify-center gap-1.5"
                >
                  <Lock className="w-4 h-4" /> Case Locked
                </button>
              ) : (
                <button
                  id={`case-card-btn-${c.id}`}
                  onClick={() => onSelectCase(c.id)}
                  className="w-full py-2.5 bg-medical-500 hover:bg-medical-700 text-white font-semibold text-sm rounded-xl shadow-md shadow-medical-100 flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Play className="w-4 h-4 fill-current" /> Begin Assessment
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

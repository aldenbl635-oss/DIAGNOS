import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';
import { TriangleAlert, Clock, Hospital, Building, Home, Award, CheckCircle2 } from 'lucide-react';

export default function Briefing({ caseId, onStartSimulation, onNavigate }) {
  const [caseBrief, setCaseBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [facilityTier, setFacilityTier] = useState("tertiary");

  useEffect(() => {
    async function fetchBrief() {
      try {
        const data = await api.getCase(caseId);
        setCaseBrief(data);
      } catch (err) {
        setError('Failed to load case briefing.');
      } finally {
        setLoading(false);
      }
    }
    fetchBrief();
  }, [caseId]);

  const handleBegin = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const session = await api.startSimulation(caseId, facilityTier);
      onStartSimulation(session.id);
    } catch (err) {
      setError(err.message || 'Failed to start simulation session.');
      setSubmitting(false);
    }
  };

  if (loading) return <Loader text="Retrieving clinical file briefing..." />;
  if (error && !caseBrief) return (
    <div className="max-w-md mx-auto my-12 text-center space-y-4 bg-red-900/20 p-6 rounded-xl border border-red-900/50">
      <h3 className="font-bold text-red-500">Briefing Error</h3>
      <p className="text-sm text-red-400">{error}</p>
      <button onClick={() => onNavigate('cases')} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-semibold">
        Back to Library
      </button>
    </div>
  );

  return (
    <div className="min-h-screen pt-12 pb-24 px-4 sm:px-6 lg:px-8 font-sans text-slate-300 flex flex-col items-center justify-start bg-[#060B12]">

      {/* Main Card */}
      <div className="w-full max-w-3xl relative overflow-hidden bg-[#0F1420] border border-[#1e293b] rounded-2xl p-8 md:p-10 shadow-2xl animate-slide-up">

        <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-teal-400 to-transparent opacity-60"></div>

        {/* Header Alert */}
        <div className="flex items-start gap-5 mb-8">
          <div className="w-12 h-12 shrink-0 bg-[#25131C] border border-red-900/30 rounded-xl flex items-center justify-center mt-1">
            <span className="text-red-500 font-bold text-lg">!</span>
          </div>
          <div className="space-y-1">
            <h1 className="text-xl sm:text-2xl pt-1 font-extrabold text-white tracking-tight">
              A patient has arrived in the Emergency Department
            </h1>
            <p className="text-sm sm:text-[15px] text-slate-400">
              Presenting with: "{caseBrief.chief_complaint}"
            </p>
          </div>
        </div>

        {/* Instructions */}
        <div className="space-y-6 text-[15px] leading-relaxed text-slate-300">
          <p>
            You have been asked to <span className="font-bold text-white">assess this patient</span>. You do not know the diagnosis.
          </p>
          <p>
            Gather the history. Ask whatever questions you need. Perform a physical<br className="hidden sm:block" />
            examination if appropriate. Request investigations. Update your clinical reasoning<br className="hidden sm:block" />
            as new evidence appears.
          </p>
          <p>
            When you are ready to make your clinical decision, submit your assessment.
          </p>
        </div>

        {/* Facility Tier Selection */}
        <div className="space-y-4 pt-6">
          <div className="flex justify-between items-end border-b border-white/5 pb-2">
            <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
              <Hospital className="w-4 h-4 text-teal-500" /> PRACTICE FACILITY TIER (RESOURCE SETTING)
            </h3>
            <span className="text-[11px] font-bold text-teal-400 tracking-wide">
              {facilityTier === 'tertiary' ? 'Full Diagnostic Suite' : facilityTier === 'chc' ? 'Secondary Tier' : 'Primary Tier Only'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { id: 'tertiary', label: 'Tertiary Hospital', desc: 'Full suite: CT, Troponin, CXR, Cath Lab.', icon: Hospital },
              { id: 'chc', label: 'District CHC', desc: 'Secondary: ECG, basic labs, CXR. No CT.', icon: Building },
              { id: 'phc', label: 'Rural PHC', desc: 'Point-of-care only. Reason & triage referral.', icon: Home },
            ].map(tier => {
              const isActive = facilityTier === tier.id;
              const Icon = tier.icon;
              return (
                <button
                  key={tier.id}
                  onClick={() => setFacilityTier(tier.id)}
                  className={`relative p-5 rounded-xl text-left transition-all border ${isActive
                      ? 'border-teal-400 bg-teal-500/5 shadow-[0_0_15px_rgba(45,212,191,0.05)]'
                      : 'border-slate-800 hover:border-slate-700 bg-slate-900/40 opacity-80 hover:opacity-100'
                    }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <Icon className={`w-5 h-5 ${isActive ? 'text-teal-400' : 'text-slate-500'}`} />
                    {isActive && <CheckCircle2 className="w-4 h-4 text-teal-400 absolute top-4 right-4" />}
                  </div>
                  <div className={`font-bold text-[15px] ${isActive ? 'text-white' : 'text-slate-200'}`}>
                    {tier.label}
                  </div>
                  <div className="text-xs mt-1.5 text-slate-400 leading-snug">
                    {tier.desc}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Meta Stats */}
        <div className="grid grid-cols-[1fr_1fr_1fr] gap-4 pt-6">
          <div className="p-5 bg-[#171C28] border border-[#232D3F] rounded-xl flex flex-col items-center justify-center text-center">
            <Hospital className="w-6 h-6 text-teal-400 mb-2 opacity-90" strokeWidth={1.5} />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-1">Setting</span>
            <span className="font-extrabold text-white text-[15px]">Emergency Dept.</span>
          </div>
          <div className="p-5 bg-[#171C28] border border-[#232D3F] rounded-xl flex flex-col items-center justify-center text-center">
            <Clock className="w-6 h-6 text-teal-400 mb-2 opacity-90" strokeWidth={1.5} />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-1">Est. Duration</span>
            <span className="font-extrabold text-white text-[15px]">{caseBrief.duration_mins} mins</span>
          </div>
          <div className="p-5 bg-[#171C28] border border-[#232D3F] rounded-xl flex flex-col items-center justify-center text-center">
            <Award className="w-6 h-6 text-teal-400 mb-2 opacity-90" strokeWidth={1.5} />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-1">Difficulty</span>
            <span className="font-extrabold text-white text-[15px]">{caseBrief.difficulty}</span>
          </div>
        </div>

        {/* Clinical Reminder */}
        <div className="mt-6 p-5 bg-[#1B1612] border border-amber-700/40 rounded-xl flex gap-3 text-[14px] leading-relaxed text-slate-400">
          <TriangleAlert className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <p>
            <span className="text-amber-400 font-bold">Clinical Reminder:</span> Do not reveal the diagnosis prematurely. Your communication style affects the patient's emotional state and trust. Alarmist statements will distress the patient.
          </p>
        </div>

        {/* Enter Room Button */}
        <div className="pt-8">
          <button
            id="briefing-begin-btn"
            onClick={handleBegin}
            disabled={submitting}
            className="w-full flex items-center justify-center gap-3 px-8 py-4 bg-gradient-to-r from-teal-600 to-[#0284c7] hover:from-teal-500 hover:to-sky-500 disabled:from-slate-700 disabled:to-slate-800 text-white font-extrabold text-[15px] rounded-xl shadow-[0_4px_25px_rgba(13,148,136,0.3)] hover:shadow-[0_4px_35px_rgba(13,148,136,0.4)] transition-all"
          >
            {submitting ? 'Preparing Room...' : 'Enter Patient Room \u2192'}
          </button>
        </div>

      </div>

      {/* Unattended indicator (bottom) */}
      <div className="w-full max-w-3xl mt-8 pt-4 border-t border-[#1e293b]">
        <h3 className="text-[10px] font-extrabold text-slate-500 opacity-80 uppercase tracking-widest">
          Other Available Encounters (Unattended):
        </h3>
      </div>
    </div>
  );
}

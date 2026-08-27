import React, { useEffect, useState } from 'react';
import { api } from '../api/client';

/**
 * EncounterSetup — immersive pre-encounter briefing room.
 * Replaces the old CaseSelection + Briefing pages.
 * The student is told only what a clinician would realistically know on arrival.
 * No diagnosis. No full history. Just the initial presentation.
 */
export default function EncounterSetup({ onStartEncounter, onNavigate }) {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);
  const [phase, setPhase] = useState('loading'); // loading | ready | entering

  const loadCases = async () => {
    try {
      const data = await api.getCases();
      setCases(data);
      if (data.length > 0) {
        setSelectedCase(data[0]);
      } else {
        setSelectedCase(null);
      }
      setPhase('ready');
    } catch (err) {
      setError('Unable to connect to clinical systems.');
      setPhase('ready');
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleResetProgress = async () => {
    if (window.confirm("Are you sure you want to reset your simulation progress? This will delete your diagnostics history and let you attend to all patients again.")) {
      try {
        setError(null);
        await api.resetHistory();
        await loadCases();
      } catch (err) {
        setError(err.message || "Failed to reset simulation progress.");
      }
    }
  };

  const handleEnterRoom = async () => {
    if (!selectedCase || starting) return;
    setStarting(true);
    setPhase('entering');
    setError(null);
    try {
      const session = await api.startSimulation(selectedCase.id);
      // Small dramatic pause before entering
      await new Promise(r => setTimeout(r, 800));
      onStartEncounter(session.id);
    } catch (err) {
      setError(err.message || 'Failed to initialize patient encounter.');
      setStarting(false);
      setPhase('ready');
    }
  };

  return (
    <div className="min-h-screen encounter-room flex items-center justify-center relative overflow-hidden">
      {/* Background ambient effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(14,165,233,0.04) 0%, transparent 70%)' }} />
        <div className="absolute bottom-0 left-0 w-96 h-96 rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(20,184,166,0.03) 0%, transparent 70%)' }} />
        {/* Horizontal scan line */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-teal-500/20 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-teal-500/10 to-transparent" />
      </div>

      {/* Back to dashboard */}
      <button
        onClick={() => onNavigate('dashboard')}
        className="absolute top-6 left-6 text-xs font-semibold text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1.5"
        id="encounter-back-btn"
      >
        ← Back to Lab
      </button>

      {/* DiagnOS logo top right */}
      <div className="absolute top-6 right-6 flex items-center gap-2 opacity-50">
        <div className="w-6 h-6 bg-teal-500/20 border border-teal-500/30 rounded-lg flex items-center justify-center">
          <span className="text-teal-400 text-xs font-black">D</span>
        </div>
        <span className="text-xs font-bold text-slate-500 tracking-wide">DiagnOS</span>
      </div>

      {/* Main content card */}
      <div className={`relative z-10 w-full max-w-xl mx-4 transition-all duration-700 ${phase === 'entering' ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
        }`}>

        {/* Department header */}
        <div className="text-center mb-8 animate-fade-in-up">
          <span className="inline-block text-[10px] font-bold tracking-[0.3em] text-teal-400 uppercase mb-3 border border-teal-555 bg-teal-500/5 px-4 py-1.5 rounded-full">
            New Patient Encounter
          </span>
          <div className="flex items-center justify-center gap-3 mt-2">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-slate-700" />
            <span className="text-xs text-slate-500 font-semibold">Emergency Department — Room 4</span>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-slate-700" />
          </div>
        </div>

        {/* The encounter card */}
        <div
          className="encounter-panel rounded-2xl overflow-hidden animate-fade-in-up"
          style={{
            animationDelay: '0.1s',
            boxShadow: '0 25px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(30,45,66,0.8), inset 0 1px 0 rgba(255,255,255,0.03)'
          }}
        >
          {/* Top accent bar */}
          <div className="h-0.5 bg-gradient-to-r from-teal-600 via-teal-400 to-transparent" />

          <div className="p-8 space-y-7">
            {cases.length === 0 ? (
              <div className="text-center py-6 space-y-5">
                <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto">
                  <span className="text-emerald-400 text-2xl font-bold">✓</span>
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-bold text-white">All Patients Attended</h3>
                  <p className="text-sm text-slate-400 max-w-sm mx-auto leading-relaxed">
                    Great work! You have completed diagnostic assessments for all available patients in the Clinical Case Library.
                  </p>
                </div>

                {/* Reset Progress */}
                <button
                  onClick={handleResetProgress}
                  className="px-5 py-2.5 bg-slate-800 hover:bg-slate-750 text-teal-400 hover:text-teal-350 border border-slate-705 rounded-xl font-bold text-xs tracking-wide transition-all uppercase cursor-pointer"
                >
                  Reset Progress & Restart Library
                </button>
              </div>
            ) : (
              <>
                {/* Patient arrival indicator */}
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-red-400 text-xs font-black">!</span>
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white leading-tight">
                      {selectedCase
                        ? selectedCase.title === 'Atypical Chest Pain' || selectedCase.chief_complaint
                          ? 'A patient has arrived in the Emergency Department'
                          : `A patient has arrived — ${selectedCase.chief_complaint || 'condition unknown'}`
                        : 'A patient has arrived in the Emergency Department'
                      }
                    </h2>
                    <p className="text-sm text-slate-400 mt-1 leading-relaxed">
                      {selectedCase?.chief_complaint
                        ? `Presenting with: "${selectedCase.chief_complaint}"`
                        : 'Presenting with discomfort — details unknown'
                      }
                    </p>
                  </div>
                </div>

                {/* Divider */}
                <div className="h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent" />

                {/* Scenario briefing */}
                <div className="space-y-4 text-sm text-slate-300 leading-relaxed">
                  <p>
                    You have been asked to <span className="text-white font-semibold">assess this patient</span>.
                    You do not know the diagnosis.
                  </p>
                  <p>
                    Gather the history. Ask whatever questions you need.
                    Perform a physical examination if appropriate.
                    Request investigations. Update your clinical reasoning as new evidence appears.
                  </p>
                  <p className="text-slate-400">
                    When you are ready to make your clinical decision, submit your assessment.
                  </p>
                </div>

                {/* Info boxes */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { icon: '🏥', label: 'Setting', value: 'Emergency Dept.' },
                    { icon: '⏱', label: 'Est. Duration', value: `${selectedCase?.duration_mins || 20} mins` },
                    { icon: '📊', label: 'Difficulty', value: selectedCase?.difficulty || 'Intermediate' },
                  ].map(({ icon, label, value }) => (
                    <div key={label} className="encounter-surface rounded-xl p-3 text-center">
                      <div className="text-lg mb-1">{icon}</div>
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</div>
                      <div className="text-xs font-bold text-slate-200 mt-0.5">{value}</div>
                    </div>
                  ))}
                </div>

                {/* Warning */}
                <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/15 rounded-xl p-4">
                  <span className="text-amber-400 text-sm shrink-0 mt-0.5">⚠</span>
                  <p className="text-xs text-amber-200/70 leading-relaxed">
                    <span className="font-semibold text-amber-300">Clinical Reminder:</span> Do not reveal the
                    diagnosis prematurely. Your communication style affects the patient's emotional state and trust.
                    Alarmist statements will distress the patient.
                  </p>
                </div>

                {/* Error */}
                {error && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-xs text-red-300">
                    {error}
                  </div>
                )}

                {/* CTA button */}
                <button
                  id="enter-patient-room-btn"
                  onClick={handleEnterRoom}
                  disabled={starting || !selectedCase}
                  className="w-full py-4 rounded-xl font-bold text-sm tracking-wide transition-all duration-300 relative overflow-hidden group cursor-pointer"
                  style={{
                    background: starting
                      ? 'rgba(15,23,36,0.8)'
                      : 'linear-gradient(135deg, #0d9488 0%, #0284c7 100%)',
                    boxShadow: starting ? 'none' : '0 8px 32px rgba(13,148,136,0.35)',
                    color: 'white',
                  }}
                >
                  <span className="relative z-10 flex items-center justify-center gap-3">
                    {starting ? (
                      <>
                        <span className="flex gap-1">
                          <span className="typing-dot w-1.5 h-1.5 rounded-full bg-teal-400 inline-block animate-bounce" />
                          <span className="typing-dot w-1.5 h-1.5 rounded-full bg-teal-400 inline-block animate-bounce [animation-delay:0.2s]" />
                          <span className="typing-dot w-1.5 h-1.5 rounded-full bg-teal-400 inline-block animate-bounce [animation-delay:0.4s]" />
                        </span>
                        Entering patient room...
                      </>
                    ) : (
                      <>
                        Enter Patient Room
                        <span className="text-lg">→</span>
                      </>
                    )}
                  </span>
                  {!starting && (
                    <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  )}
                </button>

                {/* Multiple cases selector (future-ready) */}
                {cases.length > 1 && (
                  <div className="pt-1 border-t border-slate-800">
                    <p className="text-[10px] font-semibold text-slate-600 mb-2 uppercase tracking-wider">Other available encounters (Unattended):</p>
                    <div className="flex flex-wrap gap-2">
                      {cases.map(c => (
                        <button
                          key={c.id}
                          onClick={() => setSelectedCase(c)}
                          className={`text-[10px] font-bold px-2.5 py-1 rounded-lg border transition-all cursor-pointer ${selectedCase?.id === c.id
                              ? 'border-teal-500/40 bg-teal-500/10 text-teal-400'
                              : 'border-slate-700 bg-slate-800/50 text-slate-500 hover:border-slate-600 hover:text-slate-400'
                            }`}
                        >
                          {c.title}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Footer note */}
        <p className="text-center text-[10px] text-slate-600 mt-6 animate-fade-in" style={{ animationDelay: '0.3s' }}>
          Educational simulation only — not a real clinical tool
        </p>
      </div>
    </div>
  );
}

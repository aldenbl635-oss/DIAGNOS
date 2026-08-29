import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';
import { 
  HeartPulse, 
  Clock, 
  Award, 
  Activity, 
  ArrowRight,
  ShieldCheck,
  Building2,
  Building,
  Home,
  CheckCircle2
} from 'lucide-react';

export default function Briefing({ caseId, onStartSimulation, onNavigate }) {
  const [caseBrief, setCaseBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [facilityTier, setFacilityTier] = useState('tertiary'); // 'tertiary' | 'chc' | 'phc'

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
    <div className="max-w-md mx-auto my-12 text-center space-y-4 bg-red-50 p-6 rounded-xl border border-red-100">
      <h3 className="font-bold text-red-800">Briefing Error</h3>
      <p className="text-sm text-red-650">{error}</p>
      <button onClick={() => onNavigate('cases')} className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-sm font-semibold">
        Back to Library
      </button>
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-xl p-8 space-y-8 animate-slide-up">
        
        {/* Header */}
        <div className="flex justify-between items-start gap-4 border-b border-slate-100 pb-5">
          <div className="space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-100 px-2.5 py-1 rounded-md">
              {caseBrief.specialty}
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-1">{caseBrief.title} Briefing</h1>
          </div>
          <div className="bg-medical-50 text-medical-600 p-2.5 rounded-xl border border-medical-100">
            <HeartPulse className="w-6 h-6 animate-pulse-slow" />
          </div>
        </div>

        {/* Case Metadata */}
        <div className="grid grid-cols-3 gap-4 border-b border-slate-100 pb-6 text-center">
          <div className="space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Estimated Time</span>
            <span className="text-sm font-bold text-slate-700 flex items-center justify-center gap-1">
              <Clock className="w-4 h-4 text-slate-455" /> {caseBrief.duration_mins} Minutes
            </span>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Complexity</span>
            <span className="text-sm font-bold text-slate-700 flex items-center justify-center gap-1">
              <Award className="w-4 h-4 text-slate-455" /> {caseBrief.difficulty}
            </span>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Target Budget</span>
            <span className="text-sm font-bold text-slate-700 flex items-center justify-center gap-1">
              <Activity className="w-4 h-4 text-slate-455" /> 1000 Credits
            </span>
          </div>
        </div>

        {/* Facility Tier Practice Mode Selector */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-widest">
              Select Practice Facility Tier
            </h3>
            <span className="text-[11px] font-semibold text-medical-600 bg-medical-50 px-2 py-0.5 rounded-full border border-medical-100">
              Resource Constraint Mode
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Tertiary */}
            <div
              onClick={() => setFacilityTier('tertiary')}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                facilityTier === 'tertiary'
                  ? 'border-medical-500 bg-medical-50/40 ring-2 ring-medical-500/20 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Building2 className={`w-4 h-4 ${facilityTier === 'tertiary' ? 'text-medical-600' : 'text-slate-500'}`} />
                  <h4 className="text-xs font-bold text-slate-800">Tertiary Hospital</h4>
                </div>
                {facilityTier === 'tertiary' && <CheckCircle2 className="w-4 h-4 text-medical-600 shrink-0" />}
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
                Full diagnostic suite. CT scans, Troponin, CXR, and catheterization lab available.
              </p>
            </div>

            {/* CHC */}
            <div
              onClick={() => setFacilityTier('chc')}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                facilityTier === 'chc'
                  ? 'border-medical-500 bg-medical-50/40 ring-2 ring-medical-500/20 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Building className={`w-4 h-4 ${facilityTier === 'chc' ? 'text-medical-600' : 'text-slate-500'}`} />
                  <h4 className="text-xs font-bold text-slate-800">District CHC</h4>
                </div>
                {facilityTier === 'chc' && <CheckCircle2 className="w-4 h-4 text-medical-600 shrink-0" />}
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
                Secondary hospital. ECG, basic labs, CXR available. No advanced CT/Ultrasound.
              </p>
            </div>

            {/* PHC */}
            <div
              onClick={() => setFacilityTier('phc')}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                facilityTier === 'phc'
                  ? 'border-medical-500 bg-medical-50/40 ring-2 ring-medical-500/20 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Home className={`w-4 h-4 ${facilityTier === 'phc' ? 'text-medical-600' : 'text-slate-500'}`} />
                  <h4 className="text-xs font-bold text-slate-800">Rural PHC</h4>
                </div>
                {facilityTier === 'phc' && <CheckCircle2 className="w-4 h-4 text-medical-600 shrink-0" />}
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
                Point-of-care only. Basic ECG, CBC, Glucose. Reason from history, exam, and triage referral.
              </p>
            </div>
          </div>
        </div>

        {/* Clinical Brief Details */}
        <div className="space-y-5">
          <div>
            <h3 className="text-xs font-bold text-slate-450 uppercase tracking-widest block mb-2">Patient Profile Summary</h3>
            <div className="p-4 bg-slate-50 border border-slate-200/50 rounded-xl grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm font-bold text-slate-700">
              <div>Age: <span className="font-semibold text-slate-550">{caseBrief.patient_age}</span></div>
              <div>Sex: <span className="font-semibold text-slate-550">{caseBrief.patient_sex}</span></div>
              <div className="col-span-2 sm:col-span-1">Chief Complaint: <span className="font-semibold text-red-600">"{caseBrief.chief_complaint}"</span></div>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-450 uppercase tracking-widest block">Scenario Instructions</h3>
            <div className="p-5 bg-slate-50 border border-slate-200/50 rounded-xl leading-relaxed text-sm font-medium text-slate-600">
              <p>
                The patient reports feeling uncomfortable for approximately 30 minutes. You are the attending clinician at a{' '}
                <strong className="text-slate-800 uppercase">
                  {facilityTier === 'phc' ? 'Rural Primary Health Centre (PHC)' : facilityTier === 'chc' ? 'Community Health Centre (CHC)' : 'Tertiary Care Hospital'}
                </strong>.
              </p>
              <p className="mt-3">
                Conduct targeted diagnostic history taking, perform physical examinations, and order available investigations. 
                In resource-constrained tiers, investigations outside the facility capabilities are disabled—you must evaluate red flags and formulate an accurate triage disposition (local management vs. emergency referral).
              </p>
            </div>
          </div>

          <div className="p-4 bg-amber-50/60 border border-amber-250/50 rounded-xl flex gap-3 text-xs text-amber-800">
            <ShieldCheck className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Evaluation Warning:</strong> This simulation evaluates your reasoning workflow and referral triage competency. Make sure to update your differential diagnoses list confidence values as you discover new evidence.
            </p>
          </div>
        </div>

        {/* Begin CTA */}
        <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <button
            onClick={() => onNavigate('cases')}
            className="w-full sm:w-auto px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-650 font-bold text-sm rounded-xl transition-all"
          >
            Back to Library
          </button>
          <button
            id="briefing-begin-btn"
            onClick={handleBegin}
            disabled={submitting}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3 bg-medical-500 hover:bg-medical-700 disabled:bg-slate-350 text-white font-bold text-sm rounded-xl shadow-lg shadow-medical-100/60 transition-all duration-200"
          >
            {submitting ? 'Initializing Workspace...' : 'Begin Clinical Assessment'}
            <ArrowRight className="w-4 h-4 animate-pulse-slow" />
          </button>
        </div>

      </div>
    </div>
  );
}

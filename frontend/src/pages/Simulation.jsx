import React, { useEffect, useState, useRef } from 'react';
import { 
  HeartPulse, 
  Clock, 
  DollarSign, 
  Send, 
  Plus, 
  Trash2, 
  Stethoscope, 
  FileText, 
  AlertCircle,
  HelpCircle,
  TrendingUp,
  FileHeart,
  ChevronRight,
  ShieldAlert,
  Building2,
  Building,
  Home,
  Lock,
  Share2
} from 'lucide-react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';

export default function Simulation({ sessionId, onNavigate, onSimulationComplete }) {
  const [session, setSession] = useState(null);
  const [caseBrief, setCaseBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingMsg, setSendingMsg] = useState(false);
  const [question, setQuestion] = useState('');
  
  // Simulation states
  const [messages, setMessages] = useState([]);
  const [discoveredHistory, setDiscoveredHistory] = useState([]);
  const [examsRevealed, setExamsRevealed] = useState({});
  const [investigationsOrdered, setInvestigationsOrdered] = useState({});
  const [activeTab, setActiveTab] = useState('exams'); // exams, investigations, differentials
  
  // Timer & Budget
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [remainingResources, setRemainingResources] = useState(1000);
  
  // Differential Diagnosis
  const [differentials, setDifferentials] = useState([
    { diagnosis: 'Acute coronary syndrome', confidence: 30 }
  ]);
  const [newDiagName, setNewDiagName] = useState('');

  // Submit Modal/Form
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [finalDiag, setFinalDiag] = useState('Acute coronary syndrome');
  const [immediatePriority, setImmediatePriority] = useState('');
  const [justification, setJustification] = useState('');
  const [disposition, setDisposition] = useState('manage_locally'); // manage_locally | refer | treat_symptomatically
  const [submittingEvaluation, setSubmittingEvaluation] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  
  const chatEndRef = useRef(null);

  // Load Session and Case data
  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getSession(sessionId);
        const { session: sess, case: caseData, chat_messages, exams_revealed, investigations_ordered } = data;

        setSession(sess);
        setCaseBrief(caseData);
        setMessages(chat_messages);
        setExamsRevealed(exams_revealed);
        setInvestigationsOrdered(investigations_ordered);
        setRemainingResources(sess.remaining_resources);
        setElapsedSeconds(sess.elapsed_seconds);

        if (sess.differential_diagnoses && sess.differential_diagnoses.length > 0) {
          setDifferentials(sess.differential_diagnoses);
        }

        const discovered = chat_messages
          .filter(m => m.category && m.category !== 'other')
          .map(m => m.category)
          .filter((cat, idx, arr) => arr.indexOf(cat) === idx);
        setDiscoveredHistory(discovered);
      } catch (err) {
        console.error('Error loading simulation workspace:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [sessionId]);

  // Real-time client timer
  useEffect(() => {
    if (loading) return;
    const interval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [loading]);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sendingMsg]);

  // Format seconds to MM:SS
  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60);
    const remaining = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${remaining.toString().padStart(2, '0')}`;
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!question.trim() || sendingMsg) return;

    const userQuestion = question.trim();
    setQuestion('');
    setSendingMsg(true);

    // Append user question
    setMessages(prev => [...prev, { role: 'student', text: userQuestion }]);

    try {
      const response = await api.askQuestion(sessionId, userQuestion);
      
      // Append patient response
      setMessages(prev => [...prev, { 
        role: 'patient', 
        text: response.answer,
        category: response.category
      }]);

      // Deduct resource / update elapsed time if modified by backend
      setRemainingResources(response.remaining_resources);
      // Backend updates elapsed seconds, synchronize occasionally
      if (response.elapsed_seconds > elapsedSeconds) {
        setElapsedSeconds(response.elapsed_seconds);
      }

      // Add to discovered history if category is meaningful
      if (response.category && response.category !== 'other' && !discoveredHistory.includes(response.category)) {
        setDiscoveredHistory(prev => [...prev, response.category]);
      }

    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'system_error', 
        text: 'Communication error: Failed to receive response from the patient.' 
      }]);
    } finally {
      setSendingMsg(false);
    }
  };

  const handleRevealExam = async (examType) => {
    if (examsRevealed[examType]) return;

    try {
      const response = await api.performExamination(sessionId, examType);
      setExamsRevealed(prev => ({
        ...prev,
        [examType]: response.result
      }));
      setRemainingResources(response.remaining_resources);
      if (response.elapsed_seconds > elapsedSeconds) {
        setElapsedSeconds(response.elapsed_seconds);
      }
    } catch (err) {
      console.error('Error performing physical exam:', err);
    }
  };

  const handleOrderInvestigation = async (invId) => {
    if (investigationsOrdered[invId]) return;

    try {
      const response = await api.orderInvestigation(sessionId, invId);
      setInvestigationsOrdered(prev => ({
        ...prev,
        [invId]: {
          name: response.name,
          cost: response.cost,
          result: response.result,
          interpretation: response.interpretation
        }
      }));
      setRemainingResources(response.remaining_resources);
      if (response.elapsed_seconds > elapsedSeconds) {
        setElapsedSeconds(response.elapsed_seconds);
      }
    } catch (err) {
      alert(err.message || 'Failed to order investigation.');
    }
  };

  const handleUpdateConfidence = async (index, newConfidence) => {
    const updated = [...differentials];
    updated[index].confidence = parseInt(newConfidence);
    setDifferentials(updated);
    
    try {
      // Sync with backend
      await api.updateDiagnosis(sessionId, updated);
    } catch (err) {
      console.error('Error syncing differential confidence:', err);
    }
  };

  const handleAddDifferential = async () => {
    if (!newDiagName.trim()) return;
    
    // Check duplicates
    if (differentials.some(d => d.diagnosis.toLowerCase() === newDiagName.trim().toLowerCase())) {
      setNewDiagName('');
      return;
    }

    const updated = [...differentials, { diagnosis: newDiagName.trim(), confidence: 20 }];
    setDifferentials(updated);
    setNewDiagName('');

    try {
      await api.updateDiagnosis(sessionId, updated);
    } catch (err) {
      console.error('Error syncing differential add:', err);
    }
  };

  const handleRemoveDifferential = async (index) => {
    const updated = differentials.filter((_, i) => i !== index);
    setDifferentials(updated);

    try {
      await api.updateDiagnosis(sessionId, updated);
    } catch (err) {
      console.error('Error syncing differential remove:', err);
    }
  };

  const handleSubmitFinalAssessment = async (e) => {
    e.preventDefault();
    setSubmittingEvaluation(true);
    setSubmitError(null);

    const payload = {
      final_diagnosis: finalDiag,
      immediate_priority: immediatePriority,
      evidence_justification: justification,
      disposition: disposition
    };

    try {
      const results = await api.submitFinalDiagnosis(sessionId, payload);
      setShowSubmitModal(false);
      onSimulationComplete(sessionId);
    } catch (err) {
      setSubmitError(err.message || 'Failed to submit clinical decision.');
      setSubmittingEvaluation(false);
    }
  };

  const suggestedQuestions = [
    { text: "Where is the pain located?", label: "Pain Location" },
    { text: "Does the pain radiate anywhere?", label: "Radiation" },
    { text: "What were you doing when it started?", label: "Onset Context" },
    { text: "Do you smoke or have diabetes?", label: "Risk Factors" }
  ];

  const patientInitials = caseBrief?.patient_name
    ? caseBrief.patient_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : 'PT';

  const examsList = caseBrief?.examinations || [];
  const investigationsList = caseBrief?.investigations || [];

  if (loading || !caseBrief) return <Loader text="Setting up clinical workstation environment..." />;

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-50 flex flex-col">
      
      {/* Simulation Header */}
      <div className="bg-white border-b border-slate-200/80 px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-550/10 text-red-650 rounded-xl border border-red-150">
            <HeartPulse className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-extrabold text-slate-900 text-lg tracking-tight">
                Active Simulation: {caseBrief.patient_name}
              </h2>
              {/* Facility tier badge */}
              {session?.facility_tier === 'phc' ? (
                <span className="flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                  <Home className="w-3 h-3 text-amber-600 shrink-0" />
                  Rural PHC
                </span>
              ) : session?.facility_tier === 'chc' ? (
                <span className="flex items-center gap-1 text-[11px] font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                  <Building className="w-3 h-3 text-blue-600 shrink-0" />
                  District CHC
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[11px] font-bold text-medical-700 bg-medical-50 border border-medical-200 px-2 py-0.5 rounded-full">
                  <Building2 className="w-3 h-3 text-medical-600 shrink-0" />
                  Tertiary Hospital
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 mt-0.5">
              <span>{caseBrief.specialty}</span>
              <span>•</span>
              <span>Difficulty: {caseBrief.difficulty}</span>
            </div>
          </div>
        </div>

        {/* Real-time details widgets */}
        <div className="flex items-center gap-6">
          {/* Credits remaining progress */}
          <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 px-4 py-2 rounded-xl">
            <DollarSign className="w-4 h-4 text-emerald-600 shrink-0" />
            <div className="space-y-0.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Remaining Budget</span>
              <div className="flex items-center gap-2">
                <span className="text-sm font-extrabold text-slate-800">{remainingResources}</span>
                <span className="text-[10px] font-bold text-slate-400">/ 1000 cr</span>
              </div>
            </div>
            {/* Tiny mini-bar indicator */}
            <div className="w-12 bg-slate-200 rounded-full h-1 hidden sm:block">
              <div className="bg-emerald-500 h-1 rounded-full" style={{ width: `${(remainingResources/1000)*100}%` }} />
            </div>
          </div>

          {/* Time widget */}
          <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 px-4 py-2 rounded-xl">
            <Clock className="w-4 h-4 text-medical-600 shrink-0" />
            <div className="space-y-0.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Elapsed Time</span>
              <span className="text-sm font-extrabold text-slate-800 font-mono">{formatTime(elapsedSeconds)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Workstation Panels Layout */}
      <div className="flex-1 grid lg:grid-cols-12 gap-0 overflow-hidden">
        
        {/* Left Side: Patient Chart Details (3 columns) */}
        <div className="lg:col-span-3 border-r border-slate-200 bg-white flex flex-col overflow-y-auto p-5 space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest block mb-2">Patient Chart File</span>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-medical-50 border border-medical-100 text-medical-700 font-extrabold flex items-center justify-center rounded-2xl text-lg uppercase shadow-sm">
                {patientInitials}
              </div>
              <div>
                <h4 className="font-bold text-slate-900 text-sm">{caseBrief.patient_name}</h4>
                <p className="text-xs text-slate-500 font-semibold">{caseBrief.patient_age} yrs • {caseBrief.patient_sex}</p>
              </div>
            </div>
          </div>

          {/* Vitals Panel */}
          <div className="space-y-3">
            <h5 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Initial Vital Signs</h5>
            <div className="grid grid-cols-2 gap-3.5">
              <div className="p-3 bg-slate-50 border border-slate-200/50 rounded-xl space-y-0.5">
                <span className="text-[10px] font-semibold text-slate-400">Blood Pressure</span>
                <p className="font-bold text-slate-800 text-sm">{caseBrief.vitals?.bp || 'N/A'}</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200/50 rounded-xl space-y-0.5">
                <span className="text-[10px] font-semibold text-slate-400">Heart Rate</span>
                <p className="font-bold text-red-650 text-sm flex items-center gap-1.5">
                  {caseBrief.vitals?.hr || 'N/A'} <span className="w-2 h-2 rounded-full bg-red-600 animate-ping inline-block" />
                </p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200/50 rounded-xl space-y-0.5">
                <span className="text-[10px] font-semibold text-slate-400">Oxygen Sat.</span>
                <p className="font-bold text-slate-800 text-sm">{caseBrief.vitals?.spo2 || 'N/A'}</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200/50 rounded-xl space-y-0.5">
                <span className="text-[10px] font-semibold text-slate-400">Temperature</span>
                <p className="font-bold text-slate-800 text-sm">{caseBrief.vitals?.temp || 'N/A'}</p>
              </div>
            </div>
          </div>

          {/* Discovered patient history details */}
          <div className="flex-1 flex flex-col space-y-3">
            <h5 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">Discovered Case History</h5>
            <div className="flex-1 border border-slate-200/60 rounded-xl p-3.5 bg-slate-50/50 overflow-y-auto space-y-2 text-xs font-semibold">
              {discoveredHistory.length > 0 ? (
                discoveredHistory.map((cat, idx) => {
                  // Map category to nice labels
                  const labels = {
                    pain_characteristics: "Pain location & pressure details",
                    lifestyle_risk_factors: "Lifestyle: 10 cigarettes/day",
                    past_medical_history: "History: Type 2 Diabetes",
                    associated_symptoms: "Associated: Sweating & Nausea",
                    family_history: "Family: Father MI at 54",
                    medication_history: "Meds: Metformin, Lisinopril",
                    allergies: "Allergies: NKDA"
                  };
                  return (
                    <div key={idx} className="flex items-center gap-2 text-emerald-800 bg-emerald-50 border border-emerald-100 p-2.5 rounded-lg">
                      <ChevronRight className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{labels[cat] || cat.replace(/_/g, ' ')}</span>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-slate-400 text-xs font-medium space-y-2">
                  <HelpCircle className="w-8 h-8 mx-auto text-slate-300" />
                  <p>No history discovered yet. Interview the patient to populate history files.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Center: Conversation interaction window (5 columns) */}
        <div className="lg:col-span-5 flex flex-col overflow-hidden bg-slate-100/50">
          
          {/* Scrollable messages container */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`flex flex-col max-w-[85%] ${
                  msg.role === 'student' ? 'ml-auto items-end' : 'mr-auto items-start'
                }`}
              >
                {/* Category classification indicator */}
                {msg.category && msg.category !== 'other' && (
                  <span className="text-[9px] font-bold text-medical-600 bg-medical-50/80 px-2 py-0.5 rounded-full mb-1">
                    Discovered: {msg.category.replace(/_/g, ' ')}
                  </span>
                )}
                
                <div 
                  className={`p-3.5 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'student'
                      ? 'bg-medical-500 text-white rounded-br-none shadow-md shadow-medical-100/20 font-medium'
                      : msg.role === 'system_error'
                      ? 'bg-red-50 text-red-800 border border-red-150 rounded-xl text-xs'
                      : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-sm font-medium'
                  }`}
                >
                  {msg.text}
                </div>
                <span className="text-[9px] font-semibold text-slate-400 mt-1 px-1">
                  {msg.role === 'student' ? 'Student Attending' : 'Patient'}
                </span>
              </div>
            ))}

            {sendingMsg && (
              <div className="flex items-center gap-1.5 p-3 bg-white border border-slate-200 rounded-2xl rounded-bl-none max-w-sm mr-auto text-slate-400 text-xs font-semibold animate-pulse">
                Patient is responding...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick-suggest questions bar */}
          <div className="bg-white border-t border-slate-200 px-4 py-3 flex gap-2 overflow-x-auto shrink-0 select-none">
            {suggestedQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuestion(q.text);
                }}
                className="shrink-0 bg-slate-50 hover:bg-slate-100 border border-slate-200/80 hover:border-slate-350 text-[10px] text-slate-650 font-bold px-3 py-1.5 rounded-lg transition-colors"
              >
                {q.label}
              </button>
            ))}
          </div>

          {/* Chat input box */}
          <form onSubmit={handleSendMessage} className="bg-white border-t border-slate-200 p-4 shrink-0 flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={`Ask ${caseBrief.patient_name?.split(' ')[0] || 'the patient'} about symptoms, history, and risk factors...`}
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 transition-all font-medium"
            />
            <button
              id="chat-send-btn"
              type="submit"
              disabled={sendingMsg || !question.trim()}
              className="bg-medical-500 hover:bg-medical-700 disabled:bg-slate-200 text-white disabled:text-slate-400 p-2.5 rounded-xl shadow-md shadow-medical-100 transition-all"
            >
              <Send className="w-5 h-5 fill-current" />
            </button>
          </form>
        </div>

        {/* Right Side: Tab tools panel (exams, tests, differentials) (4 columns) */}
        <div className="lg:col-span-4 border-l border-slate-200 bg-white flex flex-col overflow-hidden">
          
          {/* Tab Navigation header */}
          <div className="grid grid-cols-3 border-b border-slate-200 bg-slate-50 shrink-0">
            <button
              id="sim-tab-btn-exams"
              onClick={() => setActiveTab('exams')}
              className={`py-3 text-xs font-bold text-center border-b-2 transition-all ${
                activeTab === 'exams'
                  ? 'border-medical-550 text-medical-600 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              Examinations
            </button>
            <button
              id="sim-tab-btn-tests"
              onClick={() => setActiveTab('tests')}
              className={`py-3 text-xs font-bold text-center border-b-2 transition-all ${
                activeTab === 'tests'
                  ? 'border-medical-550 text-medical-600 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              Investigations
            </button>
            <button
              id="sim-tab-btn-diffs"
              onClick={() => setActiveTab('diffs')}
              className={`py-3 text-xs font-bold text-center border-b-2 transition-all ${
                activeTab === 'diffs'
                  ? 'border-medical-550 text-medical-600 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              Clinical Reasoning
            </button>
          </div>

          {/* Scrollable Tab details */}
          <div className="flex-1 overflow-y-auto p-4">
            
            {/* Tab 1: Physical Examinations */}
            {activeTab === 'exams' && (
              <div className="space-y-4">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Select exam to request findings</p>
                <div className="space-y-3">
                  {examsList.map((exam) => {
                    const revealed = examsRevealed[exam.type];
                    return (
                      <div key={exam.type} className="border border-slate-200/80 rounded-xl p-3.5 bg-slate-50/50 space-y-2">
                        <div className="flex justify-between items-center">
                          <div>
                            <h6 className="text-xs font-bold text-slate-800">{exam.name}</h6>
                            <span className="text-[10px] font-semibold text-slate-400 capitalize">{exam.type.replace(/_/g, ' ')} exam</span>
                          </div>
                          {!revealed ? (
                            <button
                              id={`exam-reveal-btn-${exam.type}`}
                              onClick={() => handleRevealExam(exam.type)}
                              className="flex items-center gap-1 text-[10px] font-bold bg-medical-50 hover:bg-medical-100 text-medical-700 px-3 py-1.5 border border-medical-250/50 rounded-lg transition-colors shrink-0"
                            >
                              <Stethoscope className="w-3.5 h-3.5" /> Request
                            </button>
                          ) : (
                            <span className="text-[9px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded uppercase tracking-wide shrink-0">
                              Revealed
                            </span>
                          )}
                        </div>
                        {revealed && (
                          <div className="bg-white border border-slate-200/50 p-2.5 rounded-lg text-xs leading-relaxed text-slate-700 font-semibold italic">
                            "{revealed}"
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 2: Investigations Ordering */}
            {activeTab === 'tests' && (
              <div className="space-y-4">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Order diagnostic labs and imaging</p>
                <div className="space-y-3">
                  {investigationsList.map((inv) => {
                    const ordered = investigationsOrdered[inv.id];
                    const tier = session?.facility_tier || 'tertiary';
                    const isAvailable = inv.is_available_this_session !== undefined
                      ? inv.is_available_this_session
                      : (!inv.available_at || inv.available_at.includes(tier));

                    return (
                      <div 
                        key={inv.id} 
                        className={`border rounded-xl p-3.5 space-y-3 transition-all ${
                          !isAvailable 
                            ? 'border-slate-200 bg-slate-100/70' 
                            : 'border-slate-200/80 bg-slate-50/50'
                        }`}
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <div className="flex items-center gap-2">
                              <h6 className={`text-xs font-bold ${!isAvailable ? 'text-slate-500' : 'text-slate-800'}`}>
                                {inv.name}
                              </h6>
                              {!isAvailable && (
                                <span className="text-[9px] font-bold text-amber-750 bg-amber-100/80 border border-amber-250 px-1.5 py-0.2 rounded">
                                  Not at {tier.toUpperCase()}
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] font-semibold text-slate-400">{inv.category}</span>
                          </div>
                          <span className="text-xs font-extrabold text-slate-800 shrink-0 bg-slate-200/60 px-2 py-0.5 rounded">
                            {inv.cost} cr
                          </span>
                        </div>
                        
                        {!ordered ? (
                          isAvailable ? (
                            <button
                              id={`inv-order-btn-${inv.id}`}
                              onClick={() => handleOrderInvestigation(inv.id)}
                              className="w-full text-center py-2 bg-medical-500 hover:bg-medical-700 text-white font-bold text-xs rounded-xl shadow-sm shadow-medical-100 transition-colors"
                            >
                              Order Investigation
                            </button>
                          ) : (
                            <div className="w-full py-2 px-3 bg-slate-200/80 border border-slate-300/60 text-slate-500 font-semibold text-[11px] rounded-xl flex items-center justify-center gap-1.5 text-center cursor-not-allowed">
                              <Lock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              <span>Not available at this facility — refer if needed</span>
                            </div>
                          )
                        ) : (
                          <div className="bg-white border border-slate-200/60 p-3 rounded-lg space-y-2 text-xs leading-relaxed">
                            <div>
                              <strong className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Test Result:</strong>
                              <span className="font-semibold text-slate-700">{ordered.result}</span>
                            </div>
                            <div className="border-t border-slate-100 pt-2 bg-slate-50/60 -mx-3 -mb-3 p-2.5 rounded-b-lg">
                              <strong className="text-[10px] font-bold text-medical-600 uppercase tracking-wider block">Clinical Interpretation:</strong>
                              <span className="font-semibold text-medical-800 italic">"{ordered.interpretation}"</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 3: Clinical Reasoning (Differentials + Final Decision) */}
            {activeTab === 'diffs' && (
              <div className="space-y-6">
                
                {/* Differential Diagnoses list */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Differential Diagnoses</span>
                    <span className="text-[9px] font-bold text-slate-400">Conf. Probability %</span>
                  </div>
                  
                  <div className="space-y-3">
                    {differentials.map((diff, idx) => (
                      <div key={idx} className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 space-y-2">
                        <div className="flex justify-between items-center">
                          <h6 className="text-xs font-bold text-slate-800">{diff.diagnosis}</h6>
                          {differentials.length > 1 && (
                            <button
                              onClick={() => handleRemoveDifferential(idx)}
                              className="text-slate-450 hover:text-red-650 p-1 hover:bg-red-50 rounded transition-all shrink-0"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                        {/* Custom slider */}
                        <div className="flex items-center gap-4">
                          <input
                            type="range"
                            min="0"
                            max="100"
                            step="5"
                            value={diff.confidence}
                            onChange={(e) => handleUpdateConfidence(idx, e.target.value)}
                            className="flex-1 accent-medical-500 h-1 bg-slate-200 rounded-lg cursor-pointer"
                          />
                          <span className="text-xs font-extrabold text-slate-700 w-8 text-right shrink-0">{diff.confidence}%</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Add Differential Diagnosis inline form */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newDiagName}
                      onChange={(e) => setNewDiagName(e.target.value)}
                      placeholder="Add differential... e.g. GERD"
                      className="flex-1 bg-slate-50 border border-slate-250 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-medical-500 focus:border-medical-500 font-medium"
                    />
                    <button
                      id="diff-add-btn"
                      onClick={handleAddDifferential}
                      className="bg-slate-100 hover:bg-slate-200 border border-slate-200 hover:border-slate-350 p-2 rounded-xl text-slate-650 transition-all shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Final Submission triggers button */}
                <div className="border-t border-slate-100 pt-5">
                  <button
                    id="submit-decision-trigger-btn"
                    onClick={() => {
                      // Pre-fill final diagnosis with highest confidence diff
                      const sorted = [...differentials].sort((a,b) => b.confidence - a.confidence);
                      if (sorted.length > 0) {
                        setFinalDiag(sorted[0].diagnosis);
                      }
                      setShowSubmitModal(true);
                    }}
                    className="w-full text-center py-3 bg-red-600 hover:bg-red-750 text-white font-bold text-sm rounded-xl shadow-lg shadow-red-100/50 hover:shadow-red-200/50 transition-all duration-200 flex items-center justify-center gap-2"
                  >
                    <FileText className="w-4 h-4" /> Submit Final Decision
                  </button>
                </div>

              </div>
            )}

          </div>
        </div>

      </div>

      {/* Submitting Clinical Decision Modal / Slide up drawer */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white border border-slate-250 rounded-2xl w-full max-w-lg shadow-2xl p-6 space-y-5 animate-slide-up relative">
            <h3 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
              <FileHeart className="w-5.5 h-5.5 text-red-650" /> Clinical Assessment Submission
            </h3>
            
            {submitError && (
              <div className="bg-red-50 border border-red-100 rounded-xl p-3 text-xs text-red-700 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{submitError}</span>
              </div>
            )}

            <form onSubmit={handleSubmitFinalAssessment} className="space-y-4">
              
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700" htmlFor="submit-diagnosis">1. What is your most likely final diagnosis?</label>
                <select
                  id="submit-diagnosis"
                  value={finalDiag}
                  onChange={(e) => setFinalDiag(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 font-semibold text-slate-750"
                >
                  {differentials.map((diff, idx) => (
                    <option key={idx} value={diff.diagnosis}>{diff.diagnosis}</option>
                  ))}
                  <option value="Acute coronary syndrome">Acute coronary syndrome (ACS)</option>
                  <option value="Pulmonary embolism">Pulmonary embolism (PE)</option>
                  <option value="Aortic dissection">Aortic dissection</option>
                  <option value="Gastroesophageal reflux disease">Gastroesophageal reflux disease (GERD)</option>
                  <option value="Pericarditis">Pericarditis</option>
                  <option value="Pneumonia">Pneumonia</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700" htmlFor="submit-priority">2. What is the immediate clinical management priority?</label>
                <textarea
                  id="submit-priority"
                  required
                  rows={2}
                  value={immediatePriority}
                  onChange={(e) => setImmediatePriority(e.target.value)}
                  placeholder="e.g. Activate cardiac catheterization lab for immediate percutaneous coronary intervention (PCI). Administer loading dose of aspirin (325mg) and nitroglycerin."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 font-medium text-slate-700 leading-relaxed"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700" htmlFor="submit-evidence">3. What evidence most strongly supports your diagnosis?</label>
                <textarea
                  id="submit-evidence"
                  required
                  rows={3}
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="e.g. 12-lead ECG confirms acute inferior STEMI with 2mm ST-elevation in leads II, III, aVF. The patient has multiple cardiac risk factors (diabetes, hypertension, smoking) and complains of pressure-like chest pain radiating to his left arm accompanied by sweating and nausea. Troponin I was elevated at 1.85 ng/mL."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 font-medium text-slate-700 leading-relaxed"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">4. Facility Triage & Referral Disposition</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <div
                    onClick={() => setDisposition('manage_locally')}
                    className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                      disposition === 'manage_locally'
                        ? 'border-medical-500 bg-medical-50/50 text-medical-800 ring-2 ring-medical-500/20 font-bold'
                        : 'border-slate-200 hover:border-slate-300 text-slate-650 bg-slate-50 font-medium'
                    }`}
                  >
                    <div className="mb-0.5">Manage Locally</div>
                    <p className="text-[10px] text-slate-500 font-normal leading-tight">Treat and monitor at current facility</p>
                  </div>

                  <div
                    onClick={() => setDisposition('refer')}
                    className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                      disposition === 'refer'
                        ? 'border-red-500 bg-red-50/60 text-red-800 ring-2 ring-red-500/20 font-bold'
                        : 'border-slate-200 hover:border-slate-300 text-slate-650 bg-slate-50 font-medium'
                    }`}
                  >
                    <div className="mb-0.5 text-red-650 font-bold">Refer to Higher Tier</div>
                    <p className="text-[10px] text-slate-500 font-normal leading-tight">Emergency transfer to CHC / Tertiary center</p>
                  </div>

                  <div
                    onClick={() => setDisposition('treat_symptomatically')}
                    className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                      disposition === 'treat_symptomatically'
                        ? 'border-medical-500 bg-medical-50/50 text-medical-800 ring-2 ring-medical-500/20 font-bold'
                        : 'border-slate-200 hover:border-slate-300 text-slate-650 bg-slate-50 font-medium'
                    }`}
                  >
                    <div className="mb-0.5">Symptomatic Care</div>
                    <p className="text-[10px] text-slate-500 font-normal leading-tight">Supportive / palliative stabilization</p>
                  </div>
                </div>
              </div>

              <div className="bg-amber-50/60 border border-amber-200/50 p-3 rounded-xl flex gap-2.5 text-[10px] text-amber-800 leading-relaxed">
                <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                <span>
                  By submitting, you finalize the simulation. The system will evaluate diagnostic accuracy, triage disposition, reasoning workflow, and resource utilization.
                </span>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowSubmitModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-650 font-bold text-xs rounded-lg transition-all"
                >
                  Cancel
                </button>
                <button
                  id="submit-final-eval-btn"
                  type="submit"
                  disabled={submittingEvaluation}
                  className="px-6 py-2 bg-red-600 hover:bg-red-750 disabled:bg-slate-350 text-white font-bold text-xs rounded-lg shadow-md shadow-red-100 transition-all duration-200"
                >
                  {submittingEvaluation ? 'Grading...' : 'Finalize & Grade'}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}

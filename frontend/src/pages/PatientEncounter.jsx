import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Send, Plus, Trash2, Stethoscope, FileText, AlertCircle,
  HelpCircle, Clock, DollarSign, X, ChevronDown, Activity,
  Mic, MessageSquare, FlaskConical, GitBranch, PenLine,
} from 'lucide-react';
import { api } from '../api/client';
import PatientAvatar from '../components/Patient/PatientAvatar';
import EmotionIndicator from '../components/Patient/EmotionIndicator';

/* ─── Typing indicator ──────────────────────────────── */
function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1">
      <span className="typing-dot w-2 h-2 rounded-full bg-teal-400" />
      <span className="typing-dot w-2 h-2 rounded-full bg-teal-400" />
      <span className="typing-dot w-2 h-2 rounded-full bg-teal-400" />
    </div>
  );
}

/* ─── Vitals Panel ──────────────────────────────────── */
function VitalsPanel({ vitals }) {
  const items = [
    { key: 'hr', label: 'Heart Rate', unit: 'bpm', alert: true },
    { key: 'bp', label: 'Blood Press.', unit: '', alert: false },
    { key: 'rr', label: 'Resp. Rate', unit: '/min', alert: false },
    { key: 'spo2', label: 'SpO₂', unit: '%', alert: false },
    { key: 'temp', label: 'Temperature', unit: '', alert: false },
  ];
  return (
    <div className="grid grid-cols-2 gap-2">
      {items.map(({ key, label, unit, alert }) => {
        let val = vitals?.[key];
        if (!val) return null;

        // Prevent duplicate units e.g., "102 bpm bpm"
        if (unit && typeof val === 'string' && val.toLowerCase().endsWith(unit.toLowerCase())) {
          val = val.substring(0, val.length - unit.length).trim();
        }

        return (
          <div key={key} className="encounter-surface rounded-xl p-2.5 space-y-0.5">
            <p className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">{label}</p>
            <p className={`font-bold text-sm flex items-center gap-1 ${alert ? 'text-red-400' : 'text-slate-200'}`}>
              {val} <span className="text-[9px] font-semibold text-slate-500">{unit}</span>
              {alert && <span className="vital-pulse text-[6px] text-red-500">●</span>}
            </p>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Message bubble ────────────────────────────────── */
function MessageBubble({ msg, patientName }) {
  const isPatient = msg.role === 'patient';
  const isStudent = msg.role === 'student';
  const isSystem = msg.role === 'system_error';

  if (isSystem) {
    return (
      <div className="flex justify-center animate-message-in">
        <div className="bg-red-500/10 border border-red-500/20 text-red-300 text-xs px-4 py-2 rounded-full">
          {msg.text}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-1 max-w-[85%] animate-message-in ${isStudent ? 'ml-auto items-end' : 'mr-auto items-start'}`}>
      {/* Speaker label */}
      <span className="text-[10px] font-semibold text-slate-500 px-1">
        {isStudent ? 'You' : patientName?.split(' ')[0] || 'Patient'}
      </span>

      {/* Bubble */}
      <div
        className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${isStudent
          ? 'bg-blue-600 text-white rounded-br-none shadow-lg shadow-blue-900/30 font-medium'
          : 'encounter-surface text-slate-200 rounded-bl-none border border-slate-700/50 font-normal'
          }`}
      >
        {msg.text}
      </div>

      {/* Emotional cue (patient only) */}
      {isPatient && msg.emotional_cue && (
        <p className="text-[10px] italic text-slate-500 px-1 max-w-xs leading-snug">
          {msg.emotional_cue}
        </p>
      )}
      {isPatient && msg.communication_state && msg.communication_state !== 'neutral' && msg.communication_state !== 'calm' && (
        <div className="flex items-center gap-1 px-1">
          <EmotionIndicator emotionLabel={
            msg.communication_state === 'frightened' ? 'Frightened' :
              msg.communication_state === 'shocked' ? 'Shocked' :
                msg.communication_state === 'concerned' ? 'Concerned' :
                  (msg.communication_state === 'guarded' || msg.communication_state === 'anxious') ? 'Anxious' :
                    msg.communication_state === 'reassured' ? 'Reassured' :
                      (msg.communication_state === 'angry' || msg.communication_state === 'frustrated') ? 'Angry' :
                        (msg.communication_state === 'devastated' || msg.communication_state === 'distressed') ? 'Distressed' :
                          msg.communication_state === 'confused' ? 'Confused' : 'Calm'
          } size="sm" />
        </div>
      )}
    </div>
  );
}

/* ─── Main PatientEncounter ─────────────────────────── */
export default function PatientEncounter({ sessionId, onNavigate, onEncounterComplete }) {
  const [session, setSession] = useState(null);
  const [caseBrief, setCaseBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [emotionLabel, setEmotionLabel] = useState('Calm');
  const [emotionCue, setEmotionCue] = useState('');
  const [examsRevealed, setExamsRevealed] = useState({});
  const [investigationsOrdered, setInvestigationsOrdered] = useState({});
  const [activeTab, setActiveTab] = useState('conversation'); // conversation | examination | investigations | differential | notes
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [remainingResources, setRemainingResources] = useState(1000);
  const [differentials, setDifferentials] = useState([{ diagnosis: 'Acute coronary syndrome', confidence: 30 }]);
  const [newDiagName, setNewDiagName] = useState('');
  const [clinicalNotes, setClinicalNotes] = useState('');
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [finalDiag, setFinalDiag] = useState('');
  const [immediatePriority, setImmediatePriority] = useState('');
  const [justification, setJustification] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [mobilePanel, setMobilePanel] = useState(false);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  /* Load session */
  useEffect(() => {
    async function load() {
      try {
        const data = await api.getSession(sessionId);
        const { session: sess, case: caseData, chat_messages, exams_revealed, investigations_ordered } = data;
        setSession(sess);
        setCaseBrief(caseData);
        setExamsRevealed(exams_revealed || {});
        setInvestigationsOrdered(investigations_ordered || {});
        setRemainingResources(sess.remaining_resources);
        setElapsedSeconds(sess.elapsed_seconds);
        if (sess.differential_diagnoses?.length > 0) setDifferentials(sess.differential_diagnoses);
        // Enrich messages with emotion data if available
        setMessages(chat_messages.map(m => ({ ...m })));
        // Derive initial emotion from last message
        const lastPatient = [...chat_messages].reverse().find(m => m.role === 'patient');
        if (lastPatient?.emotion_label) setEmotionLabel(lastPatient.emotion_label);
        if (lastPatient?.emotional_cue) setEmotionCue(lastPatient.emotional_cue);
      } catch (err) {
        console.error('Error loading encounter:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [sessionId]);

  /* Client-side timer */
  useEffect(() => {
    if (loading) return;
    const t = setInterval(() => setElapsedSeconds(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [loading]);

  /* Scroll to bottom */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  /* ── Send message ── */
  const handleSend = async (e, overrideText) => {
    if (e) e.preventDefault();
    const text = (overrideText || question).trim();
    if (!text || sending) return;
    setQuestion('');
    setSending(true);
    setMessages(prev => [...prev, { role: 'student', text }]);

    try {
      const resp = await api.askQuestion(sessionId, text);
      const newMsg = {
        role: 'patient',
        text: resp.answer,
        category: resp.category,
        emotion_label: resp.emotion_label,
        emotional_cue: resp.emotional_cue,
        communication_state: resp.communication_state,
      };
      setMessages(prev => [...prev, newMsg]);
      if (resp.emotion_label) setEmotionLabel(resp.emotion_label);
      if (resp.emotional_cue) setEmotionCue(resp.emotional_cue);
      if (resp.vitals) {
        setCaseBrief(prev => prev ? { ...prev, vitals: resp.vitals } : prev);
      }
      setRemainingResources(resp.remaining_resources);
      if (resp.elapsed_seconds > elapsedSeconds) setElapsedSeconds(resp.elapsed_seconds);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'system_error', text: 'Communication error — unable to reach patient.' }]);
    } finally {
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleQuickQuestion = (q) => handleSend(null, q);

  /* ── Examination ── */
  const handleExam = async (examType) => {
    if (examsRevealed[examType]) return;
    try {
      const resp = await api.performExamination(sessionId, examType);
      setExamsRevealed(prev => ({ ...prev, [examType]: resp.result }));
      setRemainingResources(resp.remaining_resources);
      if (resp.patient_reaction) {
        const reactionMsg = {
          role: 'patient',
          text: resp.patient_reaction,
          emotion_label: emotionLabel,
        };
        setTimeout(() => {
          setMessages(prev => [...prev, reactionMsg]);
        }, 600);
      }
    } catch (err) { console.error(err); }
  };

  /* ── Investigation ── */
  const handleInvestigation = async (invId) => {
    if (investigationsOrdered[invId]) return;
    try {
      const resp = await api.orderInvestigation(sessionId, invId);
      setInvestigationsOrdered(prev => ({
        ...prev,
        [invId]: { name: resp.name, cost: resp.cost, result: resp.result, interpretation: resp.interpretation }
      }));
      setRemainingResources(resp.remaining_resources);
      if (resp.elapsed_seconds > elapsedSeconds) setElapsedSeconds(resp.elapsed_seconds);

      // Patient reacts — add contextual message from server or fallback
      const reactionVal = resp.patient_reaction || (
        resp.name?.toLowerCase().includes('ecg') || resp.name?.toLowerCase().includes('electrocardiogram')
          ? "An ECG? Is there something wrong with my heart? That's what I was afraid of..."
          : resp.name?.toLowerCase().includes('troponin') || resp.name?.toLowerCase().includes('cardiac')
            ? "What's that blood test checking for? Is it serious?"
            : resp.name?.toLowerCase().includes('ct') || resp.name?.toLowerCase().includes('scan')
              ? "A scan? Oh... that sounds serious. What are you looking for?"
              : `You've gone quiet... ${resp.name ? `Is that ${resp.name} for me?` : 'Is something wrong?'}`
      );

      const reactionMsg = {
        role: 'patient',
        text: reactionVal,
        emotion_label: emotionLabel,
      };

      setTimeout(() => {
        setMessages(prev => [...prev, reactionMsg]);
      }, 600);
    } catch (err) {
      alert(err.message || 'Failed to order investigation. Check your budget.');
    }
  };

  /* ── Differentials ── */
  const updateDiffs = async (updated) => {
    setDifferentials(updated);
    try { await api.updateDiagnosis(sessionId, updated); } catch { }
  };

  /* ── Submit ── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.submitFinalDiagnosis(sessionId, {
        final_diagnosis: finalDiag,
        immediate_priority: immediatePriority,
        evidence_justification: justification,
      });
      setShowSubmitModal(false);
      onEncounterComplete(sessionId);
    } catch (err) {
      setSubmitError(err.message || 'Failed to submit assessment.');
      setSubmitting(false);
    }
  };

  const examsList = caseBrief?.examinations || [];
  const investigationsList = caseBrief?.investigations || [];
  const patientName = caseBrief?.patient_name || 'Patient';
  const patientFirst = patientName.split(' ')[0];

  const suggestedQuestions = [
    { label: 'Initial greeting', q: `Hello, I'm the doctor. Can you tell me what brought you here today?` },
    { label: 'Pain onset', q: 'When exactly did this start, and what were you doing?' },
    { label: 'Pain character', q: 'Can you describe what the discomfort feels like?' },
    { label: 'Radiation', q: 'Does the pain spread anywhere — your arm, jaw, or back?' },
    { label: 'Associated symptoms', q: 'Are you experiencing any sweating, nausea, or shortness of breath?' },
    { label: 'Medical history', q: 'Do you have any medical conditions like diabetes or high blood pressure?' },
    { label: 'Family history', q: 'Has anyone in your family had heart problems?' },
    { label: 'Medications', q: 'Are you on any medications regularly?' },
  ];

  /* Right panel tabs config */
  const tabs = [
    { id: 'history', icon: MessageSquare, label: 'History' },
    { id: 'examination', icon: Stethoscope, label: 'Examination' },
    { id: 'investigations', icon: FlaskConical, label: 'Investigations' },
    { id: 'differential', icon: GitBranch, label: 'Differential' },
    { id: 'notes', icon: PenLine, label: 'Notes' },
  ];

  if (loading || !caseBrief) {
    return (
      <div className="min-h-screen encounter-room flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-slate-400 text-sm font-medium">Preparing patient encounter...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="encounter-room text-slate-200" style={{ position: 'fixed', inset: 0, height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', zIndex: 40 }}>

      {/* ─── TOP BAR ─────────────────────────────────────── */}
      <div
        className="shrink-0 flex items-center justify-between px-5 py-3 border-b border-slate-800/80"
        style={{ background: 'rgba(8,13,23,0.95)', backdropFilter: 'blur(8px)' }}
      >
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-teal-500/20 border border-teal-500/30 rounded-lg flex items-center justify-center">
            <span className="text-teal-400 text-xs font-black">D</span>
          </div>
          <div>
            <span className="text-xs font-bold text-slate-300">DiagnOS</span>
            <span className="text-[10px] text-slate-600 ml-2 hidden sm:inline">Virtual Patient Encounter</span>
          </div>
          <div className="hidden sm:flex items-center gap-1 ml-2 px-2 py-0.5 bg-green-500/10 border border-green-500/20 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[9px] font-bold text-green-400">Active Encounter</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Timer */}
          <div className="flex items-center gap-1.5 text-slate-400">
            <Clock className="w-3.5 h-3.5" />
            <span className="text-sm font-mono font-bold text-slate-300">{formatTime(elapsedSeconds)}</span>
          </div>
          {/* Budget */}
          <div className="hidden sm:flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs font-bold text-slate-400">{remainingResources}<span className="text-slate-600 font-normal"> cr</span></span>
          </div>
          {/* End encounter */}
          <button
            id="end-encounter-btn"
            onClick={() => setShowEndConfirm(true)}
            className="px-3 py-1.5 text-xs font-bold text-slate-400 hover:text-red-400 border border-slate-700 hover:border-red-500/40 rounded-lg transition-all duration-200"
          >
            End Encounter
          </button>
        </div>
      </div>

      {/* ─── MAIN 3-PANEL LAYOUT ─────────────────────────── */}
      <div className="flex-1 flex overflow-hidden" style={{ minHeight: 0 }}>

        {/* ── LEFT: Patient Panel ───────────────────────── */}
        <div
          className="hidden lg:flex flex-col shrink-0 border-r border-slate-800 overflow-y-auto encounter-scroll"
          style={{ width: '22%', background: '#0a1120', padding: '20px 16px' }}
        >
          {/* Avatar */}
          <div className="flex flex-col items-center gap-3 pb-5 border-b border-slate-800/60">
            <PatientAvatar emotionLabel={emotionLabel} size={160} animate />
            <div className="text-center space-y-1">
              <h3 className="font-bold text-white text-base">{patientName}</h3>
              <p className="text-xs text-slate-500">
                {caseBrief.patient_age} yrs • {caseBrief.patient_sex}
                {caseBrief.patient_occupation && ` • ${caseBrief.patient_occupation}`}
              </p>
            </div>
            <div className="flex flex-col items-center gap-1">
              <EmotionIndicator emotionLabel={emotionLabel} size="md" />
              {emotionCue && (
                <p className="text-[10px] italic text-slate-500 text-center leading-snug mt-1 max-w-[160px]">
                  {emotionCue}
                </p>
              )}
            </div>
          </div>

          {/* Vitals */}
          <div className="py-4 border-b border-slate-800/60 space-y-2">
            <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Observable Vitals</p>
            <VitalsPanel vitals={caseBrief.vitals} />
          </div>

          {/* Chief complaint */}
          <div className="py-4 space-y-2">
            <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Chief Complaint</p>
            <p className="text-xs text-slate-400 italic leading-relaxed">
              "{caseBrief.chief_complaint}"
            </p>
          </div>

          {/* Encounter phase indicator */}
          <div className="mt-auto pt-4 border-t border-slate-800/60">
            <div className="encounter-surface rounded-xl p-3">
              <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest mb-2">Budget Remaining</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full transition-all duration-500"
                    style={{
                      width: `${(remainingResources / 1000) * 100}%`,
                      background: remainingResources > 500 ? '#14b8a6' : remainingResources > 200 ? '#f59e0b' : '#ef4444'
                    }}
                  />
                </div>
                <span className="text-xs font-bold text-slate-400">{remainingResources}</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── CENTER: Conversation ──────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden" style={{ background: '#090e1a' }}>

          {/* Patient name header */}
          <div className="shrink-0 px-5 py-3 border-b border-slate-800/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-teal-500/20 border border-teal-500/30 flex items-center justify-center">
                <span className="text-teal-400 text-[10px] font-bold">
                  {patientName.split(' ').map(n => n[0]).join('').slice(0, 2)}
                </span>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-300">{patientName}</p>
                <EmotionIndicator emotionLabel={emotionLabel} size="sm" />
              </div>
            </div>
            {/* Mobile: show clinical tools toggle */}
            <button
              className="lg:hidden text-xs font-semibold text-slate-500 hover:text-slate-300 border border-slate-700 hover:border-slate-600 px-2.5 py-1.5 rounded-lg flex items-center gap-1.5"
              onClick={() => setMobilePanel(!mobilePanel)}
            >
              <Activity className="w-3.5 h-3.5" /> Clinical Tools
            </button>
          </div>

          {/* Messages scroll area */}
          <div className="flex-1 overflow-y-auto encounter-scroll px-5 py-5 space-y-4" style={{ minHeight: 0 }}>
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} patientName={patientName} />
            ))}
            {sending && (
              <div className="flex flex-col gap-1 max-w-[85%] mr-auto animate-message-in">
                <span className="text-[10px] font-semibold text-slate-500 px-1">{patientFirst}</span>
                <div className="encounter-surface border border-slate-700/50 px-4 py-3 rounded-2xl rounded-bl-none">
                  <TypingDots />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick question suggestions */}
          <div className="shrink-0 border-t border-slate-800/50 px-4 py-2 flex gap-2 overflow-x-auto encounter-scroll">
            <span className="text-[9px] font-bold text-slate-600 uppercase tracking-wider shrink-0 self-center mr-1">Ask:</span>
            {suggestedQuestions.map((sq, i) => (
              <button
                key={i}
                onClick={() => handleQuickQuestion(sq.q)}
                className="shrink-0 text-[10px] font-semibold px-3 py-1.5 rounded-lg border border-slate-700/60 text-slate-400 hover:text-teal-400 hover:border-teal-500/40 hover:bg-teal-500/5 transition-all"
              >
                {sq.label}
              </button>
            ))}
          </div>

          {/* Input bar */}
          <form onSubmit={handleSend} className="shrink-0 px-4 py-4 border-t border-slate-800/50">
            <div className="flex gap-3 items-end">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  rows={1}
                  value={question}
                  onChange={e => {
                    setQuestion(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                  }}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(e); }
                  }}
                  placeholder={`Speak to ${patientFirst}... (Enter to send, Shift+Enter for newline)`}
                  className="encounter-input w-full resize-none bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 transition-all font-normal leading-relaxed"
                  style={{ minHeight: '48px', maxHeight: '120px' }}
                />
              </div>
              <button
                id="encounter-send-btn"
                type="submit"
                disabled={sending || !question.trim()}
                className="shrink-0 w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200"
                style={{
                  background: sending || !question.trim()
                    ? 'rgba(30,45,66,0.5)'
                    : 'linear-gradient(135deg, #0d9488, #0284c7)',
                  boxShadow: question.trim() ? '0 4px 16px rgba(13,148,136,0.3)' : 'none'
                }}
              >
                <Send className={`w-4 h-4 ${sending || !question.trim() ? 'text-slate-600' : 'text-white fill-current'}`} />
              </button>
            </div>
          </form>
        </div>

        {/* ── RIGHT: Clinical Workspace ─────────────────── */}
        <div
          className={`${mobilePanel ? 'flex' : 'hidden'} lg:flex flex-col shrink-0 border-l border-slate-800 overflow-hidden`}
          style={{ width: mobilePanel ? '100%' : '28%', background: '#0c1425', position: mobilePanel ? 'absolute' : 'relative', inset: mobilePanel ? 0 : 'auto', zIndex: mobilePanel ? 50 : 'auto' }}
        >
          {/* Tab navigation */}
          <div className="shrink-0 border-b border-slate-800 flex overflow-x-auto encounter-scroll" style={{ background: '#080d17' }}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                onClick={() => { setActiveTab(tab.id); setMobilePanel(true); }}
                className={`shrink-0 flex flex-col items-center gap-1 px-4 py-3 text-[9px] font-bold uppercase tracking-wider border-b-2 transition-all ${activeTab === tab.id
                  ? 'border-teal-500 text-teal-400'
                  : 'border-transparent text-slate-600 hover:text-slate-400'
                  }`}
              >
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            ))}
            {mobilePanel && (
              <button onClick={() => setMobilePanel(false)} className="ml-auto px-4 text-slate-600 hover:text-slate-400">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto encounter-scroll p-4 space-y-3">

            {/* ─ History Tab ─ */}
            {activeTab === 'history' && (
              <div className="space-y-3">
                <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Discovered Patient History</p>
                {messages.filter(m => m.role === 'patient' && m.category && m.category !== 'other').length > 0 ? (
                  messages
                    .filter(m => m.role === 'patient' && m.category && m.category !== 'other')
                    .filter((m, i, arr) => arr.findIndex(x => x.category === m.category) === i)
                    .map((m, i) => (
                      <div key={i} className="encounter-surface border border-teal-500/15 rounded-xl p-3">
                        <p className="text-[9px] font-bold text-teal-400 uppercase tracking-wider mb-1">
                          {m.category.replace(/_/g, ' ')}
                        </p>
                        <p className="text-xs text-slate-300 leading-relaxed italic">"{m.text.slice(0, 140)}{m.text.length > 140 ? '...' : ''}"</p>
                      </div>
                    ))
                ) : (
                  <div className="text-center py-10 space-y-2">
                    <HelpCircle className="w-8 h-8 text-slate-700 mx-auto" />
                    <p className="text-xs text-slate-600">No history discovered yet. Ask the patient questions to reveal information.</p>
                  </div>
                )}
              </div>
            )}

            {/* ─ Examination Tab ─ */}
            {activeTab === 'examination' && (
              <div className="space-y-3">
                <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Request Physical Examination</p>
                {examsList.length > 0 ? examsList.map(exam => {
                  const revealed = examsRevealed[exam.type];
                  return (
                    <div key={exam.type} className="encounter-surface rounded-xl p-3.5 space-y-2 border border-slate-700/30">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="text-xs font-bold text-slate-300">{exam.name}</p>
                          <p className="text-[9px] text-slate-600 capitalize">{exam.type.replace(/_/g, ' ')} examination</p>
                        </div>
                        {!revealed ? (
                          <button
                            id={`exam-btn-${exam.type}`}
                            onClick={() => handleExam(exam.type)}
                            className="text-[10px] font-bold text-teal-400 border border-teal-500/30 bg-teal-500/5 hover:bg-teal-500/15 px-3 py-1.5 rounded-lg transition-all flex items-center gap-1"
                          >
                            <Stethoscope className="w-3 h-3" /> Request
                          </button>
                        ) : (
                          <span className="text-[9px] font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded uppercase">Done</span>
                        )}
                      </div>
                      {revealed && (
                        <div className="bg-slate-900/60 border border-slate-700/30 rounded-lg p-2.5 text-[11px] text-slate-300 leading-relaxed italic">
                          "{revealed}"
                        </div>
                      )}
                    </div>
                  );
                }) : (
                  <p className="text-xs text-slate-600 text-center py-8">No examinations available for this encounter.</p>
                )}
              </div>
            )}

            {/* ─ Investigations Tab ─ */}
            {activeTab === 'investigations' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Order Investigations</p>
                  <span className="text-[9px] font-bold text-slate-600">{remainingResources} cr remaining</span>
                </div>
                {investigationsList.length > 0 ? investigationsList.map(inv => {
                  const ordered = investigationsOrdered[inv.id];
                  return (
                    <div key={inv.id} className="encounter-surface rounded-xl p-3.5 space-y-2 border border-slate-700/30">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="text-xs font-bold text-slate-300">{inv.name}</p>
                          <p className="text-[9px] text-slate-600">{inv.category}</p>
                        </div>
                        <span className="text-[10px] font-bold text-slate-500 bg-slate-800 px-2 py-0.5 rounded">{inv.cost} cr</span>
                      </div>
                      {!ordered ? (
                        <button
                          id={`inv-btn-${inv.id}`}
                          onClick={() => handleInvestigation(inv.id)}
                          className="w-full py-2 text-xs font-bold text-white rounded-lg transition-all"
                          style={{ background: 'linear-gradient(135deg, #0d9488, #0284c7)' }}
                        >
                          Order Investigation
                        </button>
                      ) : (
                        <div className="space-y-2">
                          <div className="bg-slate-900/60 border border-slate-700/30 rounded-lg p-2.5">
                            <p className="text-[9px] font-bold text-slate-600 uppercase mb-1">Result:</p>
                            <p className="text-[11px] text-slate-300 leading-relaxed">{ordered.result}</p>
                          </div>
                          <div className="bg-teal-500/5 border border-teal-500/20 rounded-lg p-2.5">
                            <p className="text-[9px] font-bold text-teal-500 uppercase mb-1">Clinical Interpretation:</p>
                            <p className="text-[11px] text-teal-200 leading-relaxed italic">"{ordered.interpretation}"</p>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }) : (
                  <p className="text-xs text-slate-600 text-center py-8">No investigations available.</p>
                )}
              </div>
            )}

            {/* ─ Differential Tab ─ */}
            {activeTab === 'differential' && (
              <div className="space-y-4">
                <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Differential Diagnoses</p>
                {differentials.map((d, i) => (
                  <div key={i} className="encounter-surface rounded-xl p-3.5 space-y-2 border border-slate-700/30">
                    <div className="flex justify-between items-center">
                      <p className="text-xs font-bold text-slate-300">{d.diagnosis}</p>
                      {differentials.length > 1 && (
                        <button
                          onClick={() => updateDiffs(differentials.filter((_, j) => j !== i))}
                          className="text-slate-600 hover:text-red-400 p-1 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <input
                        type="range" min="0" max="100" step="5"
                        value={d.confidence}
                        onChange={e => updateDiffs(differentials.map((x, j) => j === i ? { ...x, confidence: +e.target.value } : x))}
                        className="flex-1 accent-teal-500 h-1 bg-slate-700 rounded-full cursor-pointer"
                      />
                      <span className="text-xs font-bold text-slate-300 w-8 text-right">{d.confidence}%</span>
                    </div>
                    {/* Confidence bar */}
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-1 rounded-full transition-all duration-300"
                        style={{
                          width: `${d.confidence}%`,
                          background: d.confidence > 60 ? '#14b8a6' : d.confidence > 30 ? '#f59e0b' : '#475569'
                        }}
                      />
                    </div>
                  </div>
                ))}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newDiagName}
                    onChange={e => setNewDiagName(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (newDiagName.trim()) { updateDiffs([...differentials, { diagnosis: newDiagName.trim(), confidence: 20 }]); setNewDiagName(''); } } }}
                    placeholder="Add diagnosis... e.g. GERD"
                    className="encounter-input flex-1 bg-slate-800/60 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-600"
                  />
                  <button
                    id="diff-add-btn"
                    onClick={() => { if (newDiagName.trim()) { updateDiffs([...differentials, { diagnosis: newDiagName.trim(), confidence: 20 }]); setNewDiagName(''); } }}
                    className="p-2 bg-slate-800 border border-slate-700 hover:border-teal-500/40 hover:bg-teal-500/10 rounded-xl text-slate-400 hover:text-teal-400 transition-all"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>

                {/* Submit clinical assessment */}
                <div className="pt-2 border-t border-slate-800">
                  <button
                    id="submit-assessment-btn"
                    onClick={() => {
                      const sorted = [...differentials].sort((a, b) => b.confidence - a.confidence);
                      setFinalDiag(sorted[0]?.diagnosis || '');
                      setShowSubmitModal(true);
                    }}
                    className="w-full py-3 rounded-xl text-sm font-bold text-white transition-all duration-200 flex items-center justify-center gap-2"
                    style={{ background: 'linear-gradient(135deg, #b91c1c, #7f1d1d)', boxShadow: '0 4px 20px rgba(185,28,28,0.3)' }}
                  >
                    <FileText className="w-4 h-4" />
                    Submit Clinical Assessment
                  </button>
                </div>
              </div>
            )}

            {/* ─ Notes Tab ─ */}
            {activeTab === 'notes' && (
              <div className="space-y-3 h-full flex flex-col">
                <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Clinical Notes</p>
                <textarea
                  value={clinicalNotes}
                  onChange={e => setClinicalNotes(e.target.value)}
                  placeholder={`Record your clinical reasoning here...\n\nExample:\n- Patient denies prior cardiac history\n- Pain exertional onset — concerning for ACS\n- Radiation to left arm noted\n- Risk factors: DM, hypertension, smoking\n\nWorking diagnosis: Acute coronary syndrome`}
                  className="encounter-input flex-1 w-full bg-slate-800/30 border border-slate-700/50 rounded-xl p-3.5 text-xs text-slate-300 placeholder-slate-600 resize-none leading-relaxed"
                  style={{ minHeight: '300px' }}
                />
              </div>
            )}

          </div>
        </div>
      </div>

      {/* ─── SUBMIT MODAL ────────────────────────────────── */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div
            className="w-full max-w-lg rounded-2xl overflow-hidden animate-slide-up"
            style={{ background: '#0f1724', border: '1px solid #1e2d42', boxShadow: '0 30px 80px rgba(0,0,0,0.8)' }}
          >
            <div className="h-0.5 bg-gradient-to-r from-red-600 via-red-400 to-transparent" />
            <div className="p-6 space-y-5">
              <div>
                <h3 className="text-lg font-bold text-white">Submit Clinical Assessment</h3>
                <p className="text-xs text-slate-500 mt-1">This will end the encounter and generate your performance report.</p>
              </div>

              {submitError && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-xs text-red-300 flex gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" /> {submitError}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Most likely diagnosis</label>
                  <select
                    value={finalDiag}
                    onChange={e => setFinalDiag(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-teal-500"
                  >
                    {differentials.map((d, i) => <option key={i} value={d.diagnosis}>{d.diagnosis}</option>)}
                    <option value="Acute coronary syndrome">Acute coronary syndrome (ACS)</option>
                    <option value="Pulmonary embolism">Pulmonary embolism (PE)</option>
                    <option value="Aortic dissection">Aortic dissection</option>
                    <option value="Gastroesophageal reflux disease">GERD</option>
                    <option value="Pericarditis">Pericarditis</option>
                    <option value="Musculoskeletal chest pain">Musculoskeletal chest pain</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Immediate management priority</label>
                  <textarea
                    required rows={2}
                    value={immediatePriority}
                    onChange={e => setImmediatePriority(e.target.value)}
                    placeholder="e.g. Activate cath lab for primary PCI. Aspirin 300mg loading dose. Continuous monitoring."
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-xs text-slate-300 placeholder-slate-600 resize-none focus:outline-none focus:border-teal-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Evidence supporting your diagnosis</label>
                  <textarea
                    required rows={3}
                    value={justification}
                    onChange={e => setJustification(e.target.value)}
                    placeholder="e.g. ECG shows ST elevation in II, III, aVF. Troponin elevated. Patient has multiple cardiac risk factors. Pressure-like chest pain with left arm radiation..."
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-xs text-slate-300 placeholder-slate-600 resize-none focus:outline-none focus:border-teal-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
                  <button type="button" onClick={() => setShowSubmitModal(false)}
                    className="px-4 py-2 text-xs font-bold text-slate-400 hover:text-slate-200 border border-slate-700 rounded-lg transition-all">
                    Cancel
                  </button>
                  <button
                    id="final-submit-btn"
                    type="submit"
                    disabled={submitting}
                    className="px-6 py-2 text-xs font-bold text-white rounded-lg transition-all"
                    style={{ background: submitting ? '#374151' : 'linear-gradient(135deg, #b91c1c, #7f1d1d)' }}
                  >
                    {submitting ? 'Processing...' : 'Submit Assessment'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* ─── END ENCOUNTER CONFIRM ───────────────────────── */}
      {showEndConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div
            className="w-full max-w-sm rounded-2xl p-6 space-y-4 animate-slide-up"
            style={{ background: '#0f1724', border: '1px solid #1e2d42' }}
          >
            <h3 className="text-base font-bold text-white">End Encounter?</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              You haven't submitted your clinical assessment yet. If you leave now, the encounter will remain in progress and you can resume it from the dashboard.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowEndConfirm(false)}
                className="flex-1 py-2 text-xs font-bold text-slate-400 border border-slate-700 rounded-lg hover:border-slate-600 transition-all"
              >
                Continue Encounter
              </button>
              <button
                onClick={() => onNavigate('dashboard')}
                className="flex-1 py-2 text-xs font-bold text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 transition-all"
              >
                Exit to Dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';
import {
  Award,
  TrendingUp,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowRight,
  Clock,
  Activity,
  History,
  CornerDownRight,
  ShieldCheck,
  Heart,
  MessageSquare
} from 'lucide-react';

export default function Results({ sessionId, onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchResults() {
      try {
        const res = await api.getResults(sessionId);
        setData(res);
      } catch (err) {
        setError(err.message || 'Failed to retrieve assessment results.');
      } finally {
        setLoading(false);
      }
    }
    fetchResults();
  }, [sessionId]);

  if (loading) return <Loader text="Analyzing clinical action logs and compiling evaluation report..." />;
  if (error) return (
    <div className="max-w-md mx-auto my-12 text-center p-6 bg-red-50 border border-red-100 rounded-xl space-y-4">
      <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
      <h3 className="font-bold text-red-800">Results Error</h3>
      <p className="text-sm text-red-650">{error}</p>
      <button onClick={() => onNavigate('dashboard')} className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-sm font-semibold">
        Back to Dashboard
      </button>
    </div>
  );

  const { session, evaluation, actions } = data;

  const scoreCategories = [
    { name: 'History Taking', score: evaluation.history_score, max: 20, desc: 'Question relevance and risk factors identification' },
    { name: 'Differential Diagnosis', score: evaluation.differential_score ?? 0, max: 15, desc: 'Hypothesis updates as evidence emerged' },
    { name: 'Investigation Selection', score: evaluation.investigation_score, max: 20, desc: 'Appropriate diagnostic selection' },
    { name: 'Evidence Interpretation', score: evaluation.evidence_interpretation_score, max: 20, desc: 'Lab & ECG findings comprehension' },
    { name: 'Clinical Reasoning', score: evaluation.reasoning_score, max: 15, desc: 'Hypothesis updates and diagnostics sequence flow' },
    { name: 'Decision Making', score: evaluation.decision_score, max: 5, desc: 'Final diagnosis accuracy' },
    { name: 'Resource Efficiency', score: evaluation.resource_efficiency_score, max: 5, desc: 'Avoidance of unnecessary high-cost tests' }
  ];

  // Helper to format timestamps to relative duration
  const getRelativeTimeStr = (actionTime, startTime) => {
    const act = new Date(actionTime);
    const start = new Date(startTime);
    const diffMs = act - start;
    const diffSecs = Math.max(0, Math.floor(diffMs / 1000));
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;
    return `+${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Dynamic case-specific expected pathway
  const expectedPath = (data.expected_pathway && data.expected_pathway.length > 0)
    ? data.expected_pathway
    : (data.case?.expected_pathway && data.case.expected_pathway.length > 0)
      ? data.case.expected_pathway
      : [
          { label: `Meet ${data.case?.patient_name || 'Patient'} (${data.case?.chief_complaint || 'Encounter Brief'})`, type: "system" },
          { label: "Targeted Clinical History & Risk Assessment", type: "question" },
          { label: "Focused Physical Examination", type: "examination" },
          { label: "Essential Diagnostic Workup", type: "investigation" },
          { label: `Diagnose ${session?.final_diagnosis || "Target Condition"}`, type: "decision" }
        ];

  // Dynamic student actions pathway for comparison
  const getStudentPathNodes = () => {
    const nodes = [];
    const patientName = data.case?.patient_name || "Patient";
    nodes.push({ label: `Encounter Review (${patientName})`, type: "system" });

    let questionCount = 0;
    const examsPerformed = new Set();
    let updatedDifferentials = false;

    // Check evaluation weaknesses/critical mistakes for wasted/unnecessary test mentions
    const unnecessaryHints = [
      ...(evaluation.weaknesses || []),
      ...(evaluation.critical_mistakes || [])
    ].join(' ').toLowerCase();

    (actions || []).forEach(act => {
      if (act.action_type === 'question') {
        questionCount++;
      } else if (act.action_type === 'examination') {
        const cleanName = (act.content || '').replace(/^Performed\s+/i, '').trim();
        if (cleanName && !examsPerformed.has(cleanName)) {
          examsPerformed.add(cleanName);
          nodes.push({ label: `Performed ${cleanName}`, type: "examination" });
        }
      } else if (act.action_type === 'investigation') {
        const invContent = (act.content || '').replace(/^Ordered\s+/i, '').trim();
        const lower = invContent.toLowerCase();
        
        // Determine if this test was unneeded based on action cost / eval flags
        const isUnnecessary = act.cost >= 350 && (
          unnecessaryHints.includes('unnecessary') ||
          unnecessaryHints.includes('waste') ||
          unnecessaryHints.includes('low-yield') ||
          unnecessaryHints.includes(lower)
        );

        if (isUnnecessary) {
          nodes.push({ label: `Wasted Cost: Ordered ${invContent}`, type: "unnecessary" });
        } else {
          nodes.push({ label: `Ordered ${invContent}`, type: "investigation" });
        }
      } else if (act.action_type === 'diagnosis_update') {
        updatedDifferentials = true;
      }
    });

    if (questionCount > 0) {
      nodes.splice(1, 0, {
        label: `Targeted Patient Interview (${questionCount} question${questionCount > 1 ? 's' : ''})`,
        type: "question"
      });
    }

    if (updatedDifferentials) {
      nodes.push({ label: "Updated Differential Hypotheses", type: "hypothesis" });
    }

    nodes.push({ label: `Submit: ${session.final_diagnosis || "Incomplete"}`, type: "decision" });

    return nodes;
  };

  const studentPath = getStudentPathNodes();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">

      {/* Top Header Card */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-lg text-xs font-semibold">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <span>Encounter Complete</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">Patient Encounter Performance Report</h1>
          <p className="text-xs text-slate-500 font-semibold">
            Encounter Session: {session.id} • Evaluated: {new Date(evaluation.created_at).toLocaleString()}
          </p>
        </div>

        {/* Score Ring / Badge */}
        <div className="flex items-center gap-4 bg-slate-50 border border-slate-200/60 p-4 rounded-2xl shrink-0">
          <div className="w-16 h-16 bg-teal-600 text-white rounded-full flex flex-col items-center justify-center shadow-lg shadow-teal-100 shrink-0">
            <span className="text-2xl font-black leading-none">{evaluation.final_score}</span>
            <span className="text-[9px] font-bold uppercase tracking-wide opacity-80 mt-0.5">score</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest block">Encounter Rating</span>
            <h4 className="text-base font-extrabold text-slate-800">
              {evaluation.final_score >= 90 ? 'Excellent Patient Encounter' : evaluation.final_score >= 80 ? 'Good Clinical Competency' : 'Requires Focused Practice'}
            </h4>
          </div>
        </div>
      </div>

      {/* Main Grid: Category scores & feedback lists */}
      <div className="grid lg:grid-cols-12 gap-8">

        {/* Category Scores breakdown (7 cols) */}
        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm lg:col-span-7 space-y-6">
          <div className="border-b border-slate-100 pb-3 flex items-center gap-2">
            <Award className="w-5 h-5 text-medical-600" />
            <h3 className="font-bold text-slate-800">Scoring Dimension Analysis</h3>
          </div>

          <div className="space-y-5">
            {scoreCategories.map((cat, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex justify-between items-baseline text-xs font-bold">
                  <span className="text-slate-800">{cat.name}</span>
                  <span className="text-slate-500">
                    <strong className="text-slate-800">{cat.score}</strong> / {cat.max}
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${(cat.score / cat.max) >= 0.85
                      ? 'bg-emerald-500'
                      : (cat.score / cat.max) >= 0.70
                        ? 'bg-medical-500'
                        : 'bg-amber-500'
                      }`}
                    style={{ width: `${(cat.score / cat.max) * 100}%` }}
                  />
                </div>
                <span className="text-[10px] font-semibold text-slate-400 block">{cat.desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Qualitative AI Summary & Strengths (5 cols) */}
        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm lg:col-span-5 flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <div className="border-b border-slate-100 pb-3 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-medical-600" />
              <h3 className="font-bold text-slate-800">Evaluator Synthesis</h3>
            </div>

            <p className="text-xs font-semibold text-slate-650 leading-relaxed italic bg-slate-50 border border-slate-100 p-4 rounded-xl">
              "{evaluation.summary}"
            </p>
          </div>

          {/* Critical mistakes card */}
          {evaluation.critical_mistakes && evaluation.critical_mistakes.length > 0 ? (
            <div className="bg-red-50 border border-red-150 p-4 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-red-750 font-bold text-xs">
                <AlertCircle className="w-4.5 h-4.5 text-red-650 shrink-0" />
                <span>Critical Mistakes Identified ({evaluation.critical_mistakes.length}):</span>
              </div>
              <ul className="list-disc pl-4 text-[11px] font-semibold text-red-700 space-y-1">
                {evaluation.critical_mistakes.map((mistake, idx) => (
                  <li key={idx}>{mistake}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="bg-emerald-50/80 border border-emerald-150 p-4 rounded-xl space-y-1.5">
              <div className="flex items-center gap-1.5 text-emerald-800 font-bold text-xs">
                <CheckCircle className="w-4.5 h-4.5 text-emerald-600 shrink-0" />
                <span>Critical Mistakes:</span>
              </div>
              <p className="text-[11px] font-semibold text-emerald-700 pl-6">
                No critical mistakes identified. Diagnostic reasoning and investigation selection aligned with clinical guidelines.
              </p>
            </div>
          )}
        </div>

      </div>

      {/* Therapeutic Communication & Empathy Card */}
      <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm space-y-6">
        <div className="border-b border-slate-100 pb-3 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-teal-650" />
          <div>
            <h3 className="font-bold text-slate-800">Bedside Manner & Therapeutic Communication Report</h3>
            <p className="text-xs text-slate-500 font-semibold mt-0.5">
              Assessing patient-centered professionalism, bedside manner stability, and therapeutic rapport.
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Professionalism & Tone progress */}
          <div className="space-y-2 bg-slate-50/50 p-4 border border-slate-100 rounded-xl">
            <div className="flex justify-between items-center text-xs font-bold">
              <span className="text-slate-700 flex items-center gap-1">
                <ShieldCheck className="w-4 h-4 text-emerald-600" /> Professionalism & Tone
              </span>
              <span className="text-slate-800 font-extrabold">{evaluation.communication_score ?? 0} / 100</span>
            </div>
            <div className="w-full bg-slate-200/70 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${(evaluation.communication_score ?? 0) >= 80 ? 'bg-emerald-500' : (evaluation.communication_score ?? 0) >= 50 ? 'bg-teal-500' : 'bg-amber-500'
                  }`}
                style={{ width: `${evaluation.communication_score ?? 0}%` }}
              />
            </div>
            <span className="text-[10px] font-semibold text-slate-400 block">Respectful language, medical ethics support, and demeanor compliance.</span>
          </div>

          {/* Empathy Score progress */}
          <div className="space-y-2 bg-slate-50/50 p-4 border border-slate-100 rounded-xl">
            <div className="flex justify-between items-center text-xs font-bold">
              <span className="text-slate-700 flex items-center gap-1">
                <Heart className="w-4 h-4 text-rose-500" /> Empathy & Social Support
              </span>
              <span className="text-slate-800 font-extrabold">{evaluation.empathy_score ?? 0} / 100</span>
            </div>
            <div className="w-full bg-slate-200/70 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${(evaluation.empathy_score ?? 0) >= 80 ? 'bg-emerald-500' : (evaluation.empathy_score ?? 0) >= 50 ? 'bg-teal-500' : 'bg-rose-500'
                  }`}
                style={{ width: `${evaluation.empathy_score ?? 0}%` }}
              />
            </div>
            <span className="text-[10px] font-semibold text-slate-400 block">Patient emotional recognition and active validating reassuring comments.</span>
          </div>

          {/* Patient Interaction Score progress */}
          <div className="space-y-2 bg-slate-50/50 p-4 border border-slate-100 rounded-xl">
            <div className="flex justify-between items-center text-xs font-bold">
              <span className="text-slate-700 flex items-center gap-1">
                <Activity className="w-4 h-4 text-teal-500" /> Bedside Manner Stability
              </span>
              <span className="text-slate-800 font-extrabold">{evaluation.patient_interaction_score ?? 0} / 100</span>
            </div>
            <div className="w-full bg-slate-200/70 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${(evaluation.patient_interaction_score ?? 0) >= 80 ? 'bg-emerald-500' : (evaluation.patient_interaction_score ?? 0) >= 50 ? 'bg-teal-500' : 'bg-amber-500'
                  }`}
                style={{ width: `${evaluation.patient_interaction_score ?? 0}%` }}
              />
            </div>
            <span className="text-[10px] font-semibold text-slate-400 block">Maintained bedside stability, avoided distress spikes, and corrected failures.</span>
          </div>
        </div>

        {/* Chronological Timeline */}
        {evaluation.emotional_timeline && evaluation.emotional_timeline.length > 0 && (() => {
          const chartWidth = 550;
          const chartHeight = 130;
          const paddingX = 40;
          const paddingY = 20;

          const points = evaluation.emotional_timeline.map((event) => {
            const turn = event.turn;
            const label = event.emotion_label;
            let val = 50;
            if (label === 'Calm') val = 90;
            else if (label === 'Reassured') val = 95;
            else if (label === 'Concerned') val = 70;
            else if (label === 'Confused') val = 60;
            else if (label === 'Anxious') val = 40;
            else if (label === 'Shocked') val = 30;
            else if (label === 'Angry') val = 25;
            else if (label === 'Frightened') val = 20;
            else if (label === 'Distressed') val = 10;
            return { turn, val, label };
          });

          let polylinePoints = '';
          let svgPoints = [];
          if (points.length > 0) {
            const minTurn = Math.min(...points.map(p => p.turn));
            const maxTurn = Math.max(...points.map(p => p.turn));
            const turnRange = maxTurn - minTurn || 1;

            const getX = (t) => paddingX + ((t - minTurn) / turnRange) * (chartWidth - paddingX * 2);
            const getY = (v) => chartHeight - paddingY - (v / 100) * (chartHeight - paddingY * 2);

            svgPoints = points.map(p => ({
              x: getX(p.turn),
              y: getY(p.val),
              label: p.label,
              turn: p.turn,
              val: p.val
            }));

            polylinePoints = svgPoints.map(p => `${p.x},${p.y}`).join(' ');
          }

          return (
            <div className="pt-4 border-t border-slate-100 space-y-4">

              {/* Visual SVG Trend Sparkline */}
              {svgPoints.length > 1 && (
                <div className="bg-slate-50 border border-slate-200/60 p-4 rounded-xl flex flex-col md:flex-row gap-4 items-center justify-between">
                  <div className="space-y-1 text-xs shrink-0 max-w-xs">
                    <h4 className="font-extrabold text-slate-800">Patient Response Timeline Graph</h4>
                    <p className="text-slate-450 leading-relaxed font-semibold">
                      Tracks patient cooperative trust and emotional levels. High valences show confidence and reassurance; steep valleys represent trauma or fear reaction spikes.
                    </p>
                  </div>
                  <div className="w-full max-w-xl bg-white p-2 border border-slate-100 rounded-lg shadow-inner flex justify-center overflow-x-auto">
                    <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="overflow-visible min-w-[450px] w-full h-[120px]">
                      {/* Grid lines */}
                      <line x1={paddingX} y1={paddingY} x2={chartWidth - paddingX} y2={paddingY} stroke="#f8fafc" strokeWidth="1" />
                      <line x1={paddingX} y1={chartHeight / 2} x2={chartWidth - paddingX} y2={chartHeight / 2} stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3" />
                      <line x1={paddingX} y1={chartHeight - paddingY} x2={chartWidth - paddingX} y2={chartHeight - paddingY} stroke="#cbd5e1" strokeWidth="1.5" />

                      {/* Legend Labels */}
                      <text x={paddingX - 8} y={paddingY + 3} textAnchor="end" className="text-[9px] font-bold fill-slate-400 font-mono">100%</text>
                      <text x={paddingX - 8} y={chartHeight / 2 + 3} textAnchor="end" className="text-[9px] font-bold fill-slate-400 font-mono">50%</text>
                      <text x={paddingX - 8} y={chartHeight - paddingY + 3} textAnchor="end" className="text-[9px] font-bold fill-slate-400 font-mono">0%</text>

                      {/* Area Fill */}
                      <polygon
                        points={`${paddingX},${chartHeight - paddingY} ${polylinePoints} ${svgPoints[svgPoints.length - 1].x},${chartHeight - paddingY}`}
                        className="fill-teal-500/5"
                      />

                      {/* Smooth Sparkline */}
                      <polyline
                        fill="none"
                        stroke="#0d9488"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={polylinePoints}
                      />

                      {/* Nodes */}
                      {svgPoints.map((node, i) => (
                        <g key={i}>
                          <circle
                            cx={node.x}
                            cy={node.y}
                            r="3.5"
                            className="fill-teal-600 stroke-white stroke-2 shadow-sm"
                          />
                          <text
                            x={node.x}
                            y={node.y - 7}
                            textAnchor="middle"
                            className="text-[8px] font-extrabold fill-slate-700"
                          >
                            {node.label}
                          </text>
                          <text
                            x={node.x}
                            y={chartHeight - paddingY + 11}
                            textAnchor="middle"
                            className="text-[8px] font-extrabold fill-slate-400"
                          >
                            Turn {node.turn}
                          </text>
                        </g>
                      ))}
                    </svg>
                  </div>
                </div>
              )}

              <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest block font-mono">Patient Emotional Journey Log</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {evaluation.emotional_timeline.map((event, index) => {
                  const labelColors = {
                    Shocked: 'bg-amber-50/80 text-amber-800 border-amber-200',
                    Frightened: 'bg-red-50/80 text-red-800 border-red-200',
                    Distressed: 'bg-purple-50/80 text-purple-800 border-purple-200',
                    Anxious: 'bg-orange-50/80 text-orange-900 border-orange-200',
                    Concerned: 'bg-yellow-50 text-yellow-800 border-yellow-205',
                    Reassured: 'bg-emerald-50/80 text-emerald-800 border-emerald-200',
                    Angry: 'bg-rose-50/80 text-rose-800 border-rose-200',
                    Confused: 'bg-blue-50/80 text-blue-800 border-blue-200',
                    Calm: 'bg-slate-50/80 text-slate-800 border-slate-200'
                  };
                  const colorClass = labelColors[event.emotion_label] || 'bg-slate-50 text-slate-700 border-slate-200';
                  return (
                    <div key={index} className={`flex items-start gap-2.5 p-3 rounded-xl border ${colorClass} text-xs font-semibold transition-all hover:shadow-sm`}>
                      <div className="w-5 h-5 bg-white/90 border border-slate-100 rounded-full flex items-center justify-center shrink-0 font-mono text-[10px] font-black shadow-sm">
                        {event.turn}
                      </div>
                      <div className="space-y-0.5">
                        <div className="font-extrabold uppercase text-[9px] tracking-wide opacity-80">{event.emotion_label}</div>
                        <div className="text-[10px] leading-tight font-medium opacity-90">{event.description}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}
      </div>

      {/* Strengths & Improvements checklists */}
      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm space-y-4">
          <h4 className="font-bold text-slate-800 text-sm border-b border-slate-100 pb-2">Demonstrated Strengths</h4>
          <div className="space-y-3">
            {evaluation.strengths.length > 0 ? (
              evaluation.strengths.map((s, idx) => (
                <div key={idx} className="flex gap-2.5 items-start text-xs font-semibold text-emerald-800">
                  <CheckCircle className="w-4.5 h-4.5 text-emerald-600 shrink-0 mt-0.5" />
                  <span>{s}</span>
                </div>
              ))
            ) : (
              <span className="text-xs text-slate-400">No major strengths highlighted in logs.</span>
            )}
          </div>
        </div>

        <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm space-y-4">
          <h4 className="font-bold text-slate-800 text-sm border-b border-slate-100 pb-2">Areas for Improvement</h4>
          <div className="space-y-3">
            {evaluation.weaknesses.length > 0 ? (
              evaluation.weaknesses.map((w, idx) => (
                <div key={idx} className="flex gap-2.5 items-start text-xs font-semibold text-amber-900">
                  <AlertCircle className="w-4.5 h-4.5 text-amber-500 shrink-0 mt-0.5" />
                  <span>{w}</span>
                </div>
              ))
            ) : (
              <span className="text-xs text-slate-400">Excellent performance. No weaknesses identified.</span>
            )}
          </div>
        </div>
      </div>

      {/* Expected vs Actual Pathways block */}
      <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm space-y-6">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="font-bold text-slate-800 text-base">Diagnostic Pathway Alignment</h3>
          <p className="text-xs text-slate-500 font-semibold mt-0.5">
            Compare the guidelines-based optimal sequence with your actual simulation sequence.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Expected path card */}
          <div className="border border-slate-200/70 p-4.5 rounded-xl bg-slate-50/50 space-y-4">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Expected High-Value Pathway</h4>
            <div className="relative pl-5 border-l-2 border-slate-200 space-y-5 py-2">
              {expectedPath.map((node, idx) => {
                const colors = {
                  system: 'bg-slate-400',
                  question: 'bg-emerald-500',
                  examination: 'bg-purple-500',
                  investigation: 'bg-medical-500',
                  decision: 'bg-teal-600',
                  hypothesis: 'bg-indigo-500',
                  unnecessary: 'bg-amber-500'
                };
                return (
                  <div key={idx} className="relative">
                    {/* Dot */}
                    <div className={`absolute -left-[26px] top-1 w-3 h-3 ${colors[node.type] || 'bg-medical-500'} border-2 border-white rounded-full`} />
                    <span className="text-xs font-bold text-slate-800">{node.label}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Student actual path card */}
          <div className="border border-slate-200/70 p-4.5 rounded-xl bg-slate-50/50 space-y-4">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Your Diagnostic Actions</h4>
            <div className="relative pl-5 border-l-2 border-slate-200 space-y-5 py-2">
              {studentPath.map((node, idx) => {
                const colors = {
                  system: 'bg-slate-400',
                  question: 'bg-emerald-500',
                  examination: 'bg-purple-500',
                  investigation: 'bg-medical-500',
                  decision: 'bg-teal-600',
                  hypothesis: 'bg-indigo-500',
                  unnecessary: 'bg-amber-500'
                };
                return (
                  <div key={idx} className="relative">
                    {/* Dot */}
                    <div className={`absolute -left-[26px] top-1 w-3 h-3 ${colors[node.type] || 'bg-slate-400'} border-2 border-white rounded-full`} />
                    <span className="text-xs font-bold text-slate-800">{node.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Reasoning timeline */}
      <div className="bg-white border border-slate-200/80 p-6 rounded-2xl shadow-sm space-y-4">
        <div className="border-b border-slate-100 pb-3 flex items-center gap-2">
          <History className="w-5 h-5 text-medical-600" />
          <h3 className="font-bold text-slate-800">Detailed Action Chronology</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-medium text-slate-600">
            <thead>
              <tr className="border-b border-slate-100 font-bold text-[10px] text-slate-400 uppercase tracking-wider">
                <th className="py-2.5">Relative Time</th>
                <th className="py-2.5">Action Category</th>
                <th className="py-2.5">Description</th>
                <th className="py-2.5 text-right">Cost (Credits)</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((act, idx) => (
                <tr key={idx} className="border-b border-slate-100/60 hover:bg-slate-50/50">
                  <td className="py-3 font-mono font-bold text-slate-500">
                    {getRelativeTimeStr(act.timestamp, session.created_at)}
                  </td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded font-bold text-[9px] uppercase tracking-wider ${act.action_type === 'question'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                      : act.action_type === 'investigation'
                        ? 'bg-medical-50 text-medical-700 border border-medical-100'
                        : act.action_type === 'examination'
                          ? 'bg-purple-50 text-purple-700 border border-purple-100'
                          : 'bg-slate-100 text-slate-650'
                      }`}>
                      {act.action_type}
                    </span>
                  </td>
                  <td className="py-3 font-bold text-slate-750">{act.content}</td>
                  <td className="py-3 text-right font-mono font-extrabold text-slate-800">
                    {act.cost > 0 ? `-${act.cost} cr` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Disclaimers & CTAs */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-4">
        <div className="flex items-center gap-2.5 text-amber-800 bg-amber-50/60 p-3 rounded-xl border border-amber-250/50 max-w-2xl text-[10px] leading-relaxed">
          <ShieldCheck className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <span>
            <strong>Disclaimer:</strong> Feedback generated above is simulated based on rules and standard clinical criteria definitions. This assessment is purely for medical training simulator demonstrations and hackathon presentation.
          </span>
        </div>
        <button
          onClick={() => onNavigate('dashboard')}
          className="w-full sm:w-auto px-6 py-3 bg-medical-500 hover:bg-medical-750 text-white font-bold text-sm rounded-xl shadow-md shadow-medical-100 transition-all duration-200 shrink-0"
        >
          Return to Dashboard
        </button>
      </div>

    </div>
  );
}

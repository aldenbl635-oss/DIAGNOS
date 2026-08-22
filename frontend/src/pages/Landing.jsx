import React from 'react';
import { 
  HeartPulse, 
  BrainCircuit, 
  Search, 
  Stethoscope, 
  TrendingUp, 
  ShieldCheck, 
  ArrowRight,
  UserCheck,
  FileSpreadsheet,
  AlertTriangle
} from 'lucide-react';

export default function Landing({ onNavigate }) {
  const steps = [
    {
      icon: <UserCheck className="w-6 h-6 text-medical-600" />,
      title: "1. Meet the Patient",
      desc: "Receive the basic case briefing (age, sex, chief complaint) and initial vitals in the ER."
    },
    {
      icon: <BrainCircuit className="w-6 h-6 text-medical-600" />,
      title: "2. Ask the Right Questions",
      desc: "Interview the patient using natural language to uncover risk factors, pain triggers, and associated symptoms."
    },
    {
      icon: <Stethoscope className="w-6 h-6 text-medical-600" />,
      title: "3. Investigate",
      desc: "Perform physical exams and order tests like ECGs or blood panels. Track your cost budget and time constraints."
    },
    {
      icon: <Search className="w-6 h-6 text-medical-600" />,
      title: "4. Interpret Evidence",
      desc: "Review results, look for abnormalities (like ST elevation), and rule out lethal conditions."
    },
    {
      icon: <TrendingUp className="w-6 h-6 text-medical-600" />,
      title: "5. Update Your Thinking",
      desc: "Continuously update your differential diagnosis and adjust confidence probabilities as new findings arrive."
    },
    {
      icon: <ShieldCheck className="w-6 h-6 text-medical-600" />,
      title: "6. Make a Decision",
      desc: "State your final diagnosis, define the immediate treatment priorities, and justify your clinical reasoning."
    },
    {
      icon: <FileSpreadsheet className="w-6 h-6 text-medical-600" />,
      title: "7. Receive a reasoning score",
      desc: "Get graded instantly by a hybrid rule + AI engine that evaluates HOW you thought, not just WHAT you diagnosed."
    }
  ];

  return (
    <div className="bg-slate-50 min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-4 sm:px-6 lg:px-8 border-b border-slate-200/50 bg-gradient-to-b from-white via-slate-50 to-slate-100/30">
        <div className="max-w-5xl mx-auto text-center space-y-8 animate-slide-up">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medical-50 border border-medical-100 rounded-full">
            <HeartPulse className="w-4 h-4 text-medical-600 animate-pulse-slow" />
            <span className="text-xs font-semibold text-medical-700 tracking-wide uppercase">AI Clinical Simulation</span>
          </div>

          <h1 className="text-5xl sm:text-6xl font-display font-extrabold text-slate-900 tracking-tight leading-tight">
            Clinical reasoning, <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-medical-600 to-teal-500">
              not just clinical recall.
            </span>
          </h1>

          <p className="max-w-2xl mx-auto text-lg sm:text-xl text-slate-600 font-medium leading-relaxed">
            An AI-powered clinical simulation platform that evaluates how medical students think, investigate, and make decisions.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              id="landing-cta-start"
              onClick={() => onNavigate('login')}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-7 py-3.5 bg-medical-500 hover:bg-medical-700 text-white font-semibold rounded-xl shadow-lg shadow-medical-100 transition-all duration-200"
            >
              Start Simulation
              <ArrowRight className="w-4 h-4" />
            </button>
            <a
              href="#how-it-works"
              className="w-full sm:w-auto flex items-center justify-center px-7 py-3.5 bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 text-slate-700 font-semibold rounded-xl transition-all duration-200"
            >
              Explore How It Works
            </a>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900">
              Medical exams test memory. <br />
              <span className="text-medical-600">Real hospitals require clinical judgment.</span>
            </h2>
            <p className="text-slate-600 text-base leading-relaxed">
              Traditional exams evaluate your ability to select multiple-choice facts under static conditions. 
              But real patients present with vague symptoms, changing conditions, and severe time pressure.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                <h4 className="font-bold text-slate-800 text-sm">Gather Evidence</h4>
                <p className="text-xs text-slate-500 mt-1">Ask natural-language questions to extract medical history.</p>
              </div>
              <div className="p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                <h4 className="font-bold text-slate-800 text-sm">Prioritize Actions</h4>
                <p className="text-xs text-slate-500 mt-1">Order tests in logical sequences while conserving resources.</p>
              </div>
              <div className="p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                <h4 className="font-bold text-slate-800 text-sm">Adapt Hypotheses</h4>
                <p className="text-xs text-slate-500 mt-1">Adjust differentials as diagnostic evidence updates.</p>
              </div>
              <div className="p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                <h4 className="font-bold text-slate-800 text-sm">Immediate Actions</h4>
                <p className="text-xs text-slate-500 mt-1">Prioritize therapy and interventions for critical states.</p>
              </div>
            </div>
          </div>
          <div className="bg-gradient-to-br from-medical-500 to-teal-500 p-8 rounded-2xl shadow-xl text-white space-y-6 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute right-0 top-0 w-48 h-48 bg-white/5 rounded-full blur-2xl" />
            <div className="border-b border-white/20 pb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-100">Simulated Clinical Workstation</span>
              <h3 className="text-xl font-bold mt-1">Atypical Chest Pain Case</h3>
            </div>
            <div className="space-y-3.5 text-sm font-medium">
              <div className="flex justify-between items-center bg-white/10 px-3.5 py-2.5 rounded-lg">
                <span>Patient Vitals:</span>
                <span className="font-mono text-teal-100 font-bold">BP 150/90, HR 102 bpm, SpO2 96%</span>
              </div>
              <div className="flex justify-between items-center bg-white/10 px-3.5 py-2.5 rounded-lg">
                <span>Ordered Investigation:</span>
                <span className="bg-teal-400/30 text-teal-100 font-bold px-2 py-0.5 rounded text-xs">ECG</span>
              </div>
              <div className="flex justify-between items-center bg-white/10 px-3.5 py-2.5 rounded-lg">
                <span>Result:</span>
                <span className="text-yellow-250 font-bold text-xs truncate max-w-[200px]">ST-segment elevation in inferior leads II, III, aVF</span>
              </div>
              <div className="flex justify-between items-center bg-white/10 px-3.5 py-2.5 rounded-lg">
                <span>Current Differential:</span>
                <span className="font-bold text-emerald-200">Acute Coronary Syndrome (85%)</span>
              </div>
            </div>
            <div className="pt-2 text-xs text-white/80 leading-relaxed italic bg-black/10 p-3 rounded-lg border border-white/10">
              "DiagnOS logs every action you make, analyzing your investigation sequences, resource efficiency, and differential updates."
            </div>
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section id="how-it-works" className="py-20 bg-white border-y border-slate-200/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto space-y-4 mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900">How DiagnOS Works</h2>
            <p className="text-slate-600">A progressive clinical simulation designed to map your logical workflow.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.slice(0, 4).map((step, idx) => (
              <div key={idx} className="p-6 bg-slate-50 border border-slate-200/50 rounded-2xl flex flex-col space-y-4">
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm">
                  {step.icon}
                </div>
                <h3 className="font-bold text-slate-800 text-lg">{step.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
          <div className="grid sm:grid-cols-3 gap-8 mt-8">
            {steps.slice(4).map((step, idx) => (
              <div key={idx} className="p-6 bg-slate-50 border border-slate-200/50 rounded-2xl flex flex-col space-y-4">
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm">
                  {step.icon}
                </div>
                <h3 className="font-bold text-slate-800 text-lg">{step.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto space-y-4 mb-16">
          <h2 className="text-3xl font-bold tracking-tight text-slate-900 font-display">Key Features</h2>
          <p className="text-slate-600">Built as a state-of-the-art clinical evaluation station.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="p-8 bg-white border border-slate-200/60 rounded-2xl shadow-sm space-y-4">
            <div className="w-10 h-10 bg-medical-50 text-medical-600 rounded-lg flex items-center justify-center font-bold">1</div>
            <h3 className="font-bold text-slate-800 text-lg">Dynamic AI Patients</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Virtual patients powered by standard LLM characters that speak in friendly patient terms and reveal information strictly when queried.
            </p>
          </div>
          <div className="p-8 bg-white border border-slate-200/60 rounded-2xl shadow-sm space-y-4">
            <div className="w-10 h-10 bg-medical-50 text-medical-600 rounded-lg flex items-center justify-center font-bold">2</div>
            <h3 className="font-bold text-slate-800 text-lg">Progressive Evidence</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Diagnostic findings are locked until ordered. Reveal ECG strips, cardiac troponin levels, and CXR interpretations step-by-step.
            </p>
          </div>
          <div className="p-8 bg-white border border-slate-200/60 rounded-2xl shadow-sm space-y-4">
            <div className="w-10 h-10 bg-medical-50 text-medical-600 rounded-lg flex items-center justify-center font-bold">3</div>
            <h3 className="font-bold text-slate-800 text-lg">Clinical Action Logger</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Every action (question, physical exam, test ordered, diagnostic adjustments) is recorded in real-time to build an assessment timeline.
            </p>
          </div>
        </div>
      </section>

      {/* Disclaimer section */}
      <footer className="bg-slate-900 text-slate-400 py-12 px-4 border-t border-slate-850">
        <div className="max-w-5xl mx-auto text-center space-y-6">
          <div className="flex items-center justify-center gap-2 text-yellow-500">
            <AlertTriangle className="w-6 h-6 shrink-0" />
            <span className="font-bold text-sm tracking-wide uppercase text-white">Educational Simulation Disclaimer</span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-3xl mx-auto">
            DiagnOS is an educational clinical simulator designed solely for medical student training, assessment, and hackathon presentation. 
            It utilizes synthetic, simulated medical scenarios and virtual AI patients. 
            It is <strong>NOT</strong> an FDA-cleared device or clinical diagnostic system, does not process real patient medical data, 
            and must <strong>NEVER</strong> be used as a real-world diagnostic tool, clinical reference, or treatment advisor.
          </p>
          <div className="text-xs text-slate-500 pt-4 border-t border-slate-800">
            &copy; {new Date().getFullYear()} DiagnOS Project. Created for hackathon demonstration. All simulated cases are synthetic.
          </div>
        </div>
      </footer>
    </div>
  );
}

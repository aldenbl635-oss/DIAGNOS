import React from 'react';
import { ShieldAlert } from 'lucide-react';

export default function Disclaimer() {
  return (
    <div id="educational-disclaimer" className="bg-amber-50 border-y border-amber-200/60 py-2.5 px-4 text-center">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-2 text-xs font-medium text-amber-800">
        <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
        <span>
          <strong>EDUCATIONAL SIMULATION ONLY:</strong> This platform is designed strictly for medical education and assessment. 
          It uses synthetic case data and virtual patients. It is <strong>NOT</strong> a real-world clinical diagnostic tool and must not be used for patient care.
        </span>
      </div>
    </div>
  );
}

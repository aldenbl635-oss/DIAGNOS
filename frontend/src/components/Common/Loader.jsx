import React from 'react';

export default function Loader({ size = 'medium', text }) {
  const spinnerSizes = {
    small: 'w-4 h-4 border-2',
    medium: 'w-8 h-8 border-3',
    large: 'w-12 h-12 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center p-6 space-y-3">
      <div 
        className={`${spinnerSizes[size]} border-slate-250 border-t-medical-500 rounded-full animate-spin`}
        role="status"
        id="loading-spinner"
      />
      {text && <span className="text-sm font-semibold text-slate-500">{text}</span>}
    </div>
  );
}

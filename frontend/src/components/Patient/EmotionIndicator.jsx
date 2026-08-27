import React from 'react';

const EMOTION_META = {
  Calm:       { label: 'Calm',       dotClass: 'emotion-dot-calm',       textClass: 'emotion-calm',       desc: 'The patient appears relaxed.' },
  Concerned:  { label: 'Concerned',  dotClass: 'emotion-dot-concerned',  textClass: 'emotion-concerned',  desc: 'The patient looks concerned and is watching you carefully.' },
  Anxious:    { label: 'Anxious',    dotClass: 'emotion-dot-anxious',    textClass: 'emotion-anxious',    desc: 'The patient is fidgeting and seems increasingly nervous.' },
  Distressed: { label: 'Distressed', dotClass: 'emotion-dot-distressed', textClass: 'emotion-distressed', desc: 'The patient appears visibly distressed.' },
  Frightened: { label: 'Frightened', dotClass: 'emotion-dot-frightened', textClass: 'emotion-frightened', desc: 'The patient looks frightened and is seeking reassurance.' },
  Shocked:    { label: 'Shocked',    dotClass: 'emotion-dot-shocked',    textClass: 'emotion-shocked',    desc: 'The patient stares wide-eyed, visibly stunned.' },
  Reassured:  { label: 'Reassured',  dotClass: 'emotion-dot-reassured',  textClass: 'emotion-reassured',  desc: 'The patient seems warmer and more comfortable speaking with you.' },
  Angry:      { label: 'Frustrated', dotClass: 'emotion-dot-angry',      textClass: 'emotion-angry',      desc: 'The patient appears frustrated and guarded.' },
  Confused:   { label: 'Confused',   dotClass: 'emotion-dot-confused',   textClass: 'emotion-confused',   desc: 'The patient looks confused.' },
};

export default function EmotionIndicator({ emotionLabel = 'Calm', showDescription = false, size = 'md' }) {
  const meta = EMOTION_META[emotionLabel] || EMOTION_META['Calm'];
  const isHigh = ['Shocked', 'Frightened', 'Distressed'].includes(emotionLabel);

  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5';
  const textSize = size === 'sm' ? 'text-[10px]' : 'text-xs';

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span
          className={`${dotSize} rounded-full ${meta.dotClass} shrink-0 ${isHigh ? 'animate-pulse' : 'animate-glow-pulse'}`}
          style={{ transition: 'background 0.6s ease, box-shadow 0.6s ease' }}
        />
        <span
          className={`${textSize} font-bold ${meta.textClass} tracking-wide`}
          style={{ transition: 'color 0.6s ease' }}
        >
          {meta.label}
        </span>
      </div>
      {showDescription && (
        <p className="text-[10px] text-slate-400 leading-snug italic pl-4">
          {meta.desc}
        </p>
      )}
    </div>
  );
}

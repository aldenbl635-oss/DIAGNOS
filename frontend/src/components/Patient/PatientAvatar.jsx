import React from 'react';

/**
 * PatientAvatar — SVG illustrated virtual patient with emotion expression states.
 * Emotion drives: eyebrow position, eye shape, mouth shape, overall tension.
 * The avatar is always the visual heart of the encounter room.
 */

const EMOTION_CONFIG = {
  Calm:       { eyebrowY: 0, eyeOpen: 1,    mouth: 'neutral',  color: '#14b8a6', shadow: 'rgba(20,184,166,0.15)' },
  Concerned:  { eyebrowY: -3, eyeOpen: 1.1,  mouth: 'slight-frown', color: '#f59e0b', shadow: 'rgba(245,158,11,0.15)' },
  Anxious:    { eyebrowY: -5, eyeOpen: 1.2,  mouth: 'frown',   color: '#f97316', shadow: 'rgba(249,115,22,0.2)' },
  Distressed: { eyebrowY: -7, eyeOpen: 1.3,  mouth: 'open',    color: '#ef4444', shadow: 'rgba(239,68,68,0.2)' },
  Frightened: { eyebrowY: -9, eyeOpen: 1.5,  mouth: 'wide',    color: '#dc2626', shadow: 'rgba(220,38,38,0.3)' },
  Shocked:    { eyebrowY: -11, eyeOpen: 1.7, mouth: 'shocked', color: '#8b5cf6', shadow: 'rgba(139,92,246,0.35)' },
  Reassured:  { eyebrowY: 1,  eyeOpen: 0.9,  mouth: 'smile',   color: '#22c55e', shadow: 'rgba(34,197,94,0.15)' },
  Angry:      { eyebrowY: 3,  eyeOpen: 1.1,  mouth: 'slight-frown', color: '#f87171', shadow: 'rgba(248,113,113,0.2)' },
  Confused:   { eyebrowY: -4, eyeOpen: 1.15, mouth: 'slight-frown', color: '#94a3b8', shadow: 'rgba(148,163,184,0.15)' },
};

function getMouthPath(type) {
  switch (type) {
    case 'smile':        return 'M 80 175 Q 100 192 120 175';
    case 'slight-frown': return 'M 80 180 Q 100 170 120 180';
    case 'frown':        return 'M 78 183 Q 100 168 122 183';
    case 'neutral':      return 'M 82 178 Q 100 180 118 178';
    case 'open':         return 'M 82 175 Q 100 195 118 175';
    case 'wide':         return 'M 78 173 Q 100 200 122 173';
    case 'shocked':      return 'M 86 172 Q 100 204 114 172';
    default:             return 'M 82 178 Q 100 180 118 178';
  }
}

export default function PatientAvatar({ emotionLabel = 'Calm', size = 200, animate = true }) {
  const config = EMOTION_CONFIG[emotionLabel] || EMOTION_CONFIG['Calm'];
  const { eyebrowY, eyeOpen, mouth, color, shadow } = config;

  const eyeScaleY = eyeOpen;
  const leftEyeY = 138 + eyebrowY * 0.3;
  const rightEyeY = 138 + eyebrowY * 0.3;
  const leftBrowY = 118 + eyebrowY;
  const rightBrowY = 118 + eyebrowY;

  const isDistressed = ['Shocked', 'Frightened', 'Distressed'].includes(emotionLabel);
  const isCalm = ['Calm', 'Reassured'].includes(emotionLabel);

  return (
    <div
      className={`relative flex items-center justify-center ${animate ? 'animate-breathe' : ''}`}
      style={{ width: size, height: size + 20 }}
    >
      {/* Glow halo behind avatar */}
      <div
        className="absolute inset-0 rounded-full transition-all duration-700"
        style={{
          boxShadow: `0 0 ${isDistressed ? '40px' : '20px'} ${shadow}`,
          background: `radial-gradient(circle at 50% 50%, ${shadow}, transparent 70%)`,
          borderRadius: '50%',
        }}
      />

      <svg
        viewBox="0 0 200 240"
        width={size}
        height={size + 20}
        xmlns="http://www.w3.org/2000/svg"
        style={{ filter: `drop-shadow(0 8px 24px ${shadow})` }}
        role="img"
        aria-label={`Patient avatar — ${emotionLabel}`}
      >
        {/* ── Neck ── */}
        <rect x="88" y="195" width="24" height="28" rx="6" fill="#d4a574" />

        {/* ── Hospital gown / shoulders ── */}
        <ellipse cx="100" cy="232" rx="52" ry="22" fill="#e2e8f0" />
        <path d="M 52 225 Q 60 215 80 218 L 80 240 Z" fill="#cbd5e1" />
        <path d="M 148 225 Q 140 215 120 218 L 120 240 Z" fill="#cbd5e1" />
        {/* Gown V-neck */}
        <path d="M 84 220 L 100 230 L 116 220" stroke="#94a3b8" strokeWidth="1.5" fill="none" />

        {/* ── Head ── */}
        <ellipse cx="100" cy="120" rx="46" ry="52" fill="#d4a574" />
        {/* Jaw line */}
        <path d="M 60 135 Q 62 178 100 190 Q 138 178 140 135" fill="#c4936a" />
        {/* Cheeks */}
        <ellipse cx="68" cy="148" rx="9" ry="7" fill="#e8917a" opacity={isDistressed ? '0.7' : '0.35'} />
        <ellipse cx="132" cy="148" rx="9" ry="7" fill="#e8917a" opacity={isDistressed ? '0.7' : '0.35'} />

        {/* ── Hair ── */}
        <path d="M 56 105 Q 58 68 100 66 Q 142 68 144 105 Q 138 82 100 80 Q 62 82 56 105 Z" fill="#4a3728" />
        {/* Gray streaks (shows age ~52) */}
        <path d="M 58 105 Q 62 82 72 78" stroke="#9ca3af" strokeWidth="2" fill="none" opacity="0.6" />
        <path d="M 142 105 Q 138 82 128 78" stroke="#9ca3af" strokeWidth="2" fill="none" opacity="0.6" />
        {/* Ears */}
        <ellipse cx="54" cy="128" rx="7" ry="9" fill="#c4936a" />
        <ellipse cx="146" cy="128" rx="7" ry="9" fill="#c4936a" />

        {/* ── Left eyebrow ── */}
        <g style={{ transition: 'transform 0.5s ease' }}>
          <path
            d={`M 72 ${leftBrowY} Q 82 ${leftBrowY - 4 + (eyebrowY < -5 ? 3 : 0)} 88 ${leftBrowY + 1}`}
            stroke="#4a3728"
            strokeWidth="2.5"
            strokeLinecap="round"
            fill="none"
          />
        </g>

        {/* ── Right eyebrow ── */}
        <g style={{ transition: 'transform 0.5s ease' }}>
          <path
            d={`M 112 ${rightBrowY + 1} Q 118 ${rightBrowY - 4 + (eyebrowY < -5 ? 3 : 0)} 128 ${rightBrowY}`}
            stroke="#4a3728"
            strokeWidth="2.5"
            strokeLinecap="round"
            fill="none"
          />
        </g>

        {/* ── Left eye ── */}
        <g style={{ transition: 'transform 0.5s ease' }}>
          {/* Eye white */}
          <ellipse cx="80" cy={leftEyeY} rx="10" ry={7 * eyeScaleY} fill="white" />
          {/* Iris */}
          <circle cx="80" cy={leftEyeY} r={4.5 * Math.min(eyeScaleY, 1.2)} fill="#5c4033" />
          {/* Pupil */}
          <circle cx="80" cy={leftEyeY} r={2.5 * Math.min(eyeScaleY, 1.2)} fill="#1a0e07" />
          {/* Highlight */}
          <circle cx="82" cy={leftEyeY - 1.5} r="1.2" fill="white" opacity="0.9" />
          {/* Upper lid */}
          <path d={`M 70 ${leftEyeY - 7 * eyeScaleY * 0.7} Q 80 ${leftEyeY - 8 * eyeScaleY} 90 ${leftEyeY - 7 * eyeScaleY * 0.7}`}
            stroke="#4a3728" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        </g>

        {/* ── Right eye ── */}
        <g style={{ transition: 'transform 0.5s ease' }}>
          <ellipse cx="120" cy={rightEyeY} rx="10" ry={7 * eyeScaleY} fill="white" />
          <circle cx="120" cy={rightEyeY} r={4.5 * Math.min(eyeScaleY, 1.2)} fill="#5c4033" />
          <circle cx="120" cy={rightEyeY} r={2.5 * Math.min(eyeScaleY, 1.2)} fill="#1a0e07" />
          <circle cx="122" cy={rightEyeY - 1.5} r="1.2" fill="white" opacity="0.9" />
          <path d={`M 110 ${rightEyeY - 7 * eyeScaleY * 0.7} Q 120 ${rightEyeY - 8 * eyeScaleY} 130 ${rightEyeY - 7 * eyeScaleY * 0.7}`}
            stroke="#4a3728" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        </g>

        {/* ── Nose ── */}
        <path d="M 98 140 Q 95 158 90 163 Q 100 167 110 163 Q 105 158 102 140 Z"
          fill="#b8805a" opacity="0.5" />

        {/* ── Mouth ── */}
        <g style={{ transition: 'd 0.5s ease' }}>
          {/* Upper lip */}
          <path d={getMouthPath(mouth)}
            stroke="#8b5a3c" strokeWidth="2" fill="none" strokeLinecap="round"
            style={{ transition: 'd 0.5s ease' }}
          />
          {/* Lips fill */}
          {(mouth === 'open' || mouth === 'wide' || mouth === 'shocked') && (
            <>
              <ellipse cx="100" cy={mouth === 'shocked' ? 190 : 187} rx={mouth === 'shocked' ? 10 : 13} ry={mouth === 'shocked' ? 12 : 8} fill="#7a3b2e" opacity="0.8" />
              <ellipse cx="100" cy={mouth === 'shocked' ? 192 : 189} rx={mouth === 'shocked' ? 7 : 10} ry={mouth === 'shocked' ? 9 : 5} fill="#4a1a10" opacity="0.9" />
            </>
          )}
        </g>

        {/* ── Sweat drop (when frightened/shocked) ── */}
        {isDistressed && (
          <g opacity="0.8">
            <ellipse cx="145" cy="108" rx="3" ry="4.5" fill="#93c5fd" />
            <circle cx="145" cy="104" r="2.5" fill="#93c5fd" />
          </g>
        )}

        {/* ── Slight wrinkles (age realism) ── */}
        <path d="M 62 130 Q 60 135 62 140" stroke="#b8805a" strokeWidth="0.8" fill="none" opacity="0.4" />
        <path d="M 138 130 Q 140 135 138 140" stroke="#b8805a" strokeWidth="0.8" fill="none" opacity="0.4" />
        <path d="M 86 167 Q 100 170 114 167" stroke="#b8805a" strokeWidth="0.8" fill="none" opacity="0.3" />

        {/* ── Emotion-colored glow outline ── */}
        <ellipse cx="100" cy="120" rx="48" ry="54" fill="none"
          stroke={color} strokeWidth="1.5" opacity="0.25"
          style={{ transition: 'stroke 0.7s ease, opacity 0.7s ease' }}
        />
      </svg>
    </div>
  );
}

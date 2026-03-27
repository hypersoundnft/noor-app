'use client';

import { useState } from 'react';
import { Camera, Languages, ShieldCheck, ChevronRight } from 'lucide-react';
import Scanner from './Scanner';
import ResultsAnalyzer from './ResultsAnalyzer';

const card: React.CSSProperties = {
  background: 'white',
  borderRadius: '16px',
  padding: '20px',
  border: '1px solid #E2E8F0',
  marginBottom: '12px',
};

const sectionLabel: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '1.2px',
  color: '#10B981',
  marginBottom: '10px',
};

function InfoSection() {
  return (
    <div style={{ paddingBottom: '24px' }}>

      {/* About */}
      <div style={card}>
        <p style={sectionLabel}>About</p>
        <p style={{ margin: 0, fontSize: '14px', color: '#64748B', lineHeight: 1.7 }}>
          Halal Lens reads the ingredient label on any packaged food and instantly flags every
          E-number, additive, and keyword that may be impermissible — so you can shop with
          confidence.
        </p>
      </div>

      {/* How to use */}
      <div style={card}>
        <p style={sectionLabel}>How to use</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {[
            { step: '1', icon: <Camera size={16} />, title: 'Photograph the label', desc: 'Tap "Scan Ingredients" and point your camera at the ingredients list on the packaging.' },
            { step: '2', icon: <span style={{ fontSize: '16px' }}>🔍</span>, title: 'Wait for analysis', desc: 'OCR extracts the text and our engine checks every detected code and keyword.' },
            { step: '3', icon: <ShieldCheck size={16} />, title: 'Read your result', desc: 'Each ingredient is rated Permissible, Doubtful, or Avoid — with a plain-English explanation.' },
          ].map((item) => (
            <div key={item.step} style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#ECFDF5', color: '#10B981', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 700, flexShrink: 0 }}>
                {item.step}
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#1E293B', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {item.icon} {item.title}
                </div>
                <div style={{ fontSize: '13px', color: '#64748B', lineHeight: 1.6 }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Supported languages */}
      <div style={card}>
        <p style={sectionLabel}>
          <Languages size={12} style={{ display: 'inline', marginRight: '5px', verticalAlign: 'middle' }} />
          Supported languages
        </p>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { flag: '🇬🇧', lang: 'English' },
            { flag: '🇮🇩', lang: 'Indonesian' },
            { flag: '🇫🇷', lang: 'French' },
          ].map(({ flag, lang }) => (
            <div key={lang} style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#F1F5F9', borderRadius: '100px', padding: '6px 14px', fontSize: '13px', fontWeight: 600, color: '#1E293B' }}>
              <span>{flag}</span> {lang}
            </div>
          ))}
        </div>
        <p style={{ margin: '12px 0 0', fontSize: '12px', color: '#94A3B8', lineHeight: 1.5 }}>
          More languages coming soon. Results may vary with low-quality images or unusual fonts.
        </p>
      </div>

      {/* Halal verification source */}
      <div style={card}>
        <p style={sectionLabel}>
          <ShieldCheck size={12} style={{ display: 'inline', marginRight: '5px', verticalAlign: 'middle' }} />
          Halal verification source
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {[
            { title: 'E-number database', desc: 'Curated list of EU food additives (E100–E999) with halal rulings based on ingredient origin and scholarly consensus.' },
            { title: 'Keyword detection', desc: 'Explicit haram terms (pork, lard, alcohol, carmine, gelatin…) are matched in English, Indonesian, and French.' },
            { title: 'Doubtful category', desc: "Ingredients with uncertain origin (e.g. glycerin, mono-/diglycerides) are flagged as Doubtful so you can investigate further or seek a scholar's opinion." },
          ].map((item) => (
            <div key={item.title} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <ChevronRight size={16} style={{ color: '#10B981', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#1E293B', marginBottom: '2px' }}>{item.title}</div>
                <div style={{ fontSize: '13px', color: '#64748B', lineHeight: 1.6 }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: '16px', padding: '12px', background: '#FFFBEB', borderRadius: '10px', border: '1px solid #FDE68A' }}>
          <p style={{ margin: 0, fontSize: '12px', color: '#92400E', lineHeight: 1.6 }}>
            <strong>Disclaimer:</strong> Halal Lens is a reference tool, not a fatwa. When in doubt,
            consult a qualified Islamic scholar or look for a certified halal label on the packaging.
          </p>
        </div>
      </div>

    </div>
  );
}

type ScanResult = { text: string; imageUrl: string };

export default function HalalLensApp() {
  const [result, setResult] = useState<ScanResult | null>(null);

  const reset = () => setResult(null);

  return (
    <>
      <style>{`
        @keyframes hl-scanline {
          0%   { transform: translateY(-30px); opacity: 0.5; }
          100% { transform: translateY(30px);  opacity: 1; }
        }
        @keyframes hl-fadeIn {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Full page — Noor light theme */}
      <div style={{
        minHeight: '100vh',
        backgroundColor: '#FAFAFA',
        display: 'flex',
        justifyContent: 'center',
        fontFamily: 'var(--font-plus-jakarta, "Plus Jakarta Sans", sans-serif)',
        color: '#1E293B',
      }}>
        <div style={{ width: '100%', maxWidth: '480px', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>

          {/* Nav */}
          <nav style={{
            position: 'sticky', top: 0, zIndex: 20,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '16px 20px',
            background: 'rgba(250,250,250,0.9)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            borderBottom: '1px solid #E2E8F0',
          }}>
            {/* Logo */}
            <div style={{ fontSize: '18px', fontWeight: 700, letterSpacing: '-0.4px', color: '#1E293B' }}>
              noor<span style={{ color: '#10B981' }}>.</span>
            </div>

            {/* Page title */}
            <div style={{ fontSize: '15px', fontWeight: 700, color: '#1E293B' }}>Halal Lens</div>

            {/* Back link */}
            <a href="/" style={{ fontSize: '13px', fontWeight: 600, color: '#64748B', textDecoration: 'none' }}>
              ← Home
            </a>
          </nav>

          {/* Content */}
          <main style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column' }}>
            {result ? (
              <ResultsAnalyzer
                rawText={result.text}
                imageUrl={result.imageUrl}
                onReset={reset}
              />
            ) : (
              <>
                <Scanner onResult={(text, imageUrl) => setResult({ text, imageUrl })} />
                <InfoSection />
              </>
            )}
          </main>

          {/* Bottom nav bar */}
          {!result && (
            <nav style={{
              display: 'flex',
              borderTop: '1px solid #E2E8F0',
              background: 'rgba(250,250,250,0.95)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              padding: '10px 0 16px',
            }}>
              {[
                { label: 'Scan', active: true, icon: '⊙' },
                { label: 'History', active: false, icon: '⊡' },
                { label: 'Search', active: false, icon: '◎' },
                { label: 'Profile', active: false, icon: '⊛' },
              ].map((item) => (
                <div key={item.label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '10px', background: item.active ? '#ECFDF5' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', color: item.active ? '#10B981' : '#94A3B8' }}>
                    {item.icon}
                  </div>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: item.active ? '#10B981' : '#94A3B8' }}>
                    {item.label}
                  </span>
                </div>
              ))}
            </nav>
          )}
        </div>
      </div>
    </>
  );
}

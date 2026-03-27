'use client';

import { useState, useEffect } from 'react';
import { ShieldCheck, ShieldX, ShieldAlert, ChevronLeft, X } from 'lucide-react';
import { analyzeIngredients, type AnalysisResult, type HalalStatus, type DetailedIngredient } from '@/lib/analyzer';

type Props = {
  rawText: string;
  imageUrl: string;
  onReset: () => void;
};

const config = {
  Permissible: {
    label: 'HALAL',
    sub: 'This product is Permissible',
    icon: ShieldCheck,
    iconBg: '#ECFDF5', iconColor: '#10B981', borderColor: '#A7F3D0',
  },
  Doubtful: {
    label: 'DOUBTFUL',
    sub: 'Requires further verification',
    icon: ShieldAlert,
    iconBg: '#FFFBEB', iconColor: '#F59E0B', borderColor: '#FDE68A',
  },
  Avoid: {
    label: 'AVOID',
    sub: 'Contains haram ingredients',
    icon: ShieldX,
    iconBg: '#FEF2F2', iconColor: '#EF4444', borderColor: '#FECACA',
  },
  Unknown: {
    label: 'UNKNOWN',
    sub: 'Unable to determine status',
    icon: ShieldAlert,
    iconBg: '#F8FAFC', iconColor: '#94A3B8', borderColor: '#E2E8F0',
  },
};

const statusPill: Record<HalalStatus, { bg: string; text: string; dot: string }> = {
  Permissible: { bg: '#ECFDF5', text: '#059669', dot: '#10B981' },
  Doubtful:    { bg: '#FFFBEB', text: '#D97706', dot: '#F59E0B' },
  Avoid:       { bg: '#FEF2F2', text: '#DC2626', dot: '#EF4444' },
  Unknown:     { bg: '#F1F5F9', text: '#64748B', dot: '#94A3B8' },
};

function Pill({ status }: { status: HalalStatus }) {
  const s = statusPill[status];
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '4px 10px', borderRadius: '100px', fontSize: '11px', fontWeight: 700, background: s.bg, color: s.text, whiteSpace: 'nowrap' }}>
      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
      {status}
    </span>
  );
}

function DetailsSheet({ items, onClose }: { items: DetailedIngredient[]; onClose: () => void }) {
  const counts = { Permissible: 0, Doubtful: 0, Avoid: 0, Unknown: 0 };
  items.forEach((i) => counts[i.status]++);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      background: 'rgba(15,23,42,0.5)',
      display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
      animation: 'hl-fadeIn 0.2s ease-out',
    }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: '#FAFAFA',
        borderRadius: '24px 24px 0 0',
        maxHeight: '85vh',
        display: 'flex', flexDirection: 'column',
        animation: 'hl-slideUp 0.3s ease-out',
      }}>
        {/* Sheet header */}
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid #E2E8F0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <div>
            <div style={{ fontSize: '17px', fontWeight: 700, color: '#1E293B' }}>Ingredient Breakdown</div>
            <div style={{ fontSize: '13px', color: '#64748B', marginTop: '2px' }}>{items.length} ingredients detected</div>
          </div>
          <button onClick={onClose} style={{ background: '#F1F5F9', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
            <X size={16} color="#64748B" />
          </button>
        </div>

        {/* Summary bar */}
        <div style={{ display: 'flex', gap: '8px', padding: '14px 20px', borderBottom: '1px solid #E2E8F0', flexShrink: 0 }}>
          {(Object.entries(counts) as [HalalStatus, number][])
            .filter(([, n]) => n > 0)
            .map(([status, n]) => {
              const s = statusPill[status];
              return (
                <div key={status} style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '5px 12px', borderRadius: '100px', background: s.bg, fontSize: '12px', fontWeight: 700, color: s.text }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: s.dot }} />
                  {n} {status}
                </div>
              );
            })}
        </div>

        {/* Scrollable list */}
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {items.map((item, i) => (
            <div key={i} style={{
              padding: '14px 20px',
              borderBottom: i < items.length - 1 ? '1px solid #F1F5F9' : 'none',
              display: 'flex', alignItems: 'flex-start', gap: '12px',
            }}>
              {/* Status dot line */}
              <div style={{ paddingTop: '4px', flexShrink: 0 }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: statusPill[item.status].dot }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: '#1E293B', lineHeight: 1.3 }}>{item.name}</div>
                  <Pill status={item.status} />
                </div>
                {item.raw.toUpperCase() !== item.name.toUpperCase() && (
                  <div style={{ fontSize: '11px', color: '#94A3B8', marginBottom: '4px', fontFamily: 'monospace' }}>{item.raw}</div>
                )}
                <div style={{ fontSize: '13px', color: '#64748B', lineHeight: 1.5 }}>{item.reason}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Safe area spacer */}
        <div style={{ height: '20px', flexShrink: 0 }} />
      </div>

      <style>{`
        @keyframes hl-slideUp {
          from { transform: translateY(100%); }
          to   { transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

export default function ResultsAnalyzer({ rawText, imageUrl, onReset }: Props) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setAnalysis(analyzeIngredients(rawText)), 300);
    return () => clearTimeout(t);
  }, [rawText]);

  if (!analysis) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '60px 24px', gap: '16px' }}>
        <div style={{ width: '180px', height: '3px', background: 'linear-gradient(90deg, transparent, #10B981, transparent)', borderRadius: '2px', animation: 'hl-scanline 1.5s ease-in-out infinite alternate' }} />
        <p style={{ color: '#64748B', margin: 0 }}>Analyzing ingredients…</p>
      </div>
    );
  }

  const c = config[analysis.status] ?? config.Unknown;
  const StatusIcon = c.icon;

  return (
    <>
      <div style={{ animation: 'hl-fadeIn 0.4s ease-out forwards' }}>
        {/* Back */}
        <button onClick={onReset} style={{ background: 'transparent', border: 'none', color: '#64748B', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '20px', cursor: 'pointer', padding: 0, fontSize: '14px', fontWeight: 600 }}>
          <ChevronLeft size={18} /> Back to Scanner
        </button>

        {/* Product image */}
        <div style={{ borderRadius: '20px', overflow: 'hidden', height: '200px', marginBottom: '20px', background: '#F1F5F9' }}>
          <img src={imageUrl} alt="Product" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>

        {/* Main result card */}
        <div style={{ background: 'white', borderRadius: '20px', padding: '24px', border: `1px solid ${c.borderColor}`, boxShadow: '0 4px 24px rgba(0,0,0,0.06)', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid #F1F5F9' }}>
            <div style={{ width: '52px', height: '52px', borderRadius: '14px', background: c.iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <StatusIcon size={28} color={c.iconColor} />
            </div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: c.iconColor, letterSpacing: '-0.5px', lineHeight: 1.1 }}>{c.label}</div>
              <div style={{ fontSize: '14px', color: '#64748B', marginTop: '2px' }}>{c.sub}</div>
              <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>Verified by Noor&apos;s database.</div>
            </div>
          </div>

          {/* Flagged ingredients (avoid/doubtful only) */}
          {analysis.ingredients.length > 0 ? (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '1px', margin: '0 0 12px' }}>Flagged Ingredients</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {analysis.ingredients.map((ing) => (
                  <div key={ing.code} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: '#F8FAFC', borderRadius: '10px', gap: '8px' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#1E293B' }}>{ing.name}</div>
                      <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px', lineHeight: 1.4 }}>{ing.description}</div>
                    </div>
                    <Pill status={ing.status} />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p style={{ margin: 0, color: '#64748B', fontSize: '14px', textAlign: 'center', padding: '8px 0' }}>
              No flagged E-numbers or keywords found.
            </p>
          )}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={onReset} style={{ flex: 1, padding: '13px', borderRadius: '12px', border: '1.5px solid #E2E8F0', background: 'white', fontSize: '14px', fontWeight: 600, color: '#1E293B', cursor: 'pointer' }}>
            Scan Another
          </button>
          <button
            onClick={() => setShowDetails(true)}
            style={{ flex: 1, padding: '13px', borderRadius: '12px', border: 'none', background: '#10B981', fontSize: '14px', fontWeight: 600, color: 'white', cursor: 'pointer', boxShadow: '0 4px 12px rgba(16,185,129,0.3)' }}
          >
            View Details
          </button>
        </div>
      </div>

      {/* Details bottom sheet */}
      {showDetails && analysis.detailedIngredients.length > 0 && (
        <DetailsSheet items={analysis.detailedIngredients} onClose={() => setShowDetails(false)} />
      )}
    </>
  );
}

'use client';

import { useRef, useState } from 'react';
import { ScanSearch, Camera } from 'lucide-react';
import { processImageWithOCR } from '@/lib/ocr';

type Props = {
  onResult: (text: string, imageUrl: string) => void;
};

export default function Scanner({ onResult }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleCapture = () => fileInputRef.current?.click();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    setPreview(url);
    setIsScanning(true);

    try {
      const text = await processImageWithOCR(file);
      onResult(text, url);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Scan failed: ${msg}`);
      setPreview(null);
      setIsScanning(false);
    }
    e.target.value = '';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '28px', padding: '24px 0' }}>
      <input
        type="file"
        accept="image/*"
        capture="environment"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {/* Viewfinder */}
      <div
        style={{
          position: 'relative',
          width: '260px',
          height: '260px',
          borderRadius: '20px',
          overflow: 'hidden',
          background: '#F1F5F9',
        }}
      >
        {/* Preview image or placeholder icon */}
        {preview ? (
          <img
            src={preview}
            alt="Scanned label"
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ScanSearch size={64} color="#CBD5E1" />
          </div>
        )}

        {/* Corner brackets */}
        {['topLeft', 'topRight', 'bottomLeft', 'bottomRight'].map((corner) => (
          <div
            key={corner}
            style={{
              position: 'absolute',
              width: '28px',
              height: '28px',
              borderColor: '#10B981',
              borderStyle: 'solid',
              borderWidth: 0,
              ...(corner === 'topLeft' && { top: 12, left: 12, borderTopWidth: 3, borderLeftWidth: 3, borderTopLeftRadius: 6 }),
              ...(corner === 'topRight' && { top: 12, right: 12, borderTopWidth: 3, borderRightWidth: 3, borderTopRightRadius: 6 }),
              ...(corner === 'bottomLeft' && { bottom: 12, left: 12, borderBottomWidth: 3, borderLeftWidth: 3, borderBottomLeftRadius: 6 }),
              ...(corner === 'bottomRight' && { bottom: 12, right: 12, borderBottomWidth: 3, borderRightWidth: 3, borderBottomRightRadius: 6 }),
            }}
          />
        ))}

        {/* Scan animation overlay */}
        {isScanning && (
          <div style={{
            position: 'absolute', inset: 0,
            background: 'rgba(15,23,42,0.35)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px',
          }}>
            <div style={{
              width: '180px', height: '3px',
              background: 'linear-gradient(90deg, transparent, #10B981, transparent)',
              boxShadow: '0 0 12px #10B981',
              borderRadius: '2px',
              animation: 'hl-scanline 1.5s ease-in-out infinite alternate',
            }} />
          </div>
        )}
      </div>

      {/* Instruction text */}
      <p style={{ margin: 0, color: '#64748B', fontSize: '14px', textAlign: 'center', maxWidth: '220px', lineHeight: 1.6 }}>
        {isScanning
          ? 'Extracting ingredients…'
          : 'Point your camera at a food label to check its halal status'}
      </p>

      {/* CTA button */}
      <button
        onClick={handleCapture}
        disabled={isScanning}
        style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          background: isScanning ? '#A7F3D0' : '#10B981',
          color: 'white', border: 'none', borderRadius: '12px',
          padding: '15px 32px', fontSize: '15px', fontWeight: 600,
          cursor: isScanning ? 'not-allowed' : 'pointer',
          boxShadow: isScanning ? 'none' : '0 4px 14px rgba(16,185,129,0.35)',
          transition: 'all 0.2s',
          width: '100%',
          justifyContent: 'center',
        }}
      >
        <Camera size={18} />
        {isScanning ? 'Analyzing…' : 'Scan Ingredients'}
      </button>
    </div>
  );
}

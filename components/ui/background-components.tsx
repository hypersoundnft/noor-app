'use client';

import React from "react";

export const Component = ({ children }: { children?: React.ReactNode }) => {
  return (
    <div className="min-h-screen w-full relative bg-white">
      {/* Noor mint green glow */}
      <div
        className="absolute inset-0 z-0 pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle at center, #10B981 0%, transparent 70%)`,
          opacity: 0.15,
          mixBlendMode: "normal",
        }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
};

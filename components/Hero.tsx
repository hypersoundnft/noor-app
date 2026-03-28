export default function Hero() {
  return (
    <section className="max-w-3xl mx-auto px-6 py-24 text-center">
      {/* Badge */}
      <div className="inline-flex items-center gap-2 bg-emerald-50 text-noor-mint border border-emerald-200 px-4 py-1.5 rounded-full text-sm font-semibold mb-7">
        ✦ Islamic companion apps
      </div>

      {/* Heading */}
      <h1 className="text-4xl md:text-5xl xl:text-[56px] font-bold tracking-tight text-noor-slate leading-tight mb-5">
        Your daily <span className="text-noor-mint">light</span>,<br />
        delivered with purpose.
      </h1>

      {/* Subtext */}
      <p className="text-base md:text-lg text-noor-muted max-w-xl mx-auto leading-relaxed mb-10">
        Noor builds tools that bring Islamic knowledge into everyday life —
        thoughtfully designed, beautifully simple.
      </p>

      {/* CTAs */}
      <div className="flex items-center justify-center gap-4 flex-wrap">
        <a
          href="https://t.me/islam_agent_bot"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-noor-mint text-white px-6 py-3.5 rounded-xl text-base font-semibold shadow-[0_4px_14px_rgba(16,185,129,0.3)] hover:bg-emerald-600 transition-colors"
        >
          ✦ Start your Quran journey
        </a>
        <a
          href="/halal-lens"
          className="inline-flex items-center gap-2 border border-noor-mint text-noor-mint px-6 py-3.5 rounded-xl text-base font-semibold hover:bg-emerald-50 transition-colors"
        >
          🔍 Try Halal Lens →
        </a>
      </div>
    </section>
  );
}

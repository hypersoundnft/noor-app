export default function Footer() {
  return (
    <footer className="border-t border-slate-200 px-6 md:px-12 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div className="text-lg font-bold tracking-tight text-noor-slate">
        noor<span className="text-noor-mint">.</span>
      </div>
      <p className="text-sm text-noor-muted text-center">
        © 2026 Noor. Illuminating the permissible.
      </p>
      <a
        href="https://t.me/islam_agent_bot"
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm text-noor-muted hover:text-noor-slate transition-colors"
      >
        Telegram →
      </a>
    </footer>
  );
}

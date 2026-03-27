export default function Nav() {
  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between px-6 md:px-12 py-4 border-b border-slate-200 bg-noor-alabaster/90 backdrop-blur-sm">
      {/* Logo */}
      <div className="text-xl font-bold tracking-tight text-noor-slate">
        noor<span className="text-noor-mint">.</span>
      </div>

      {/* Scroll links — hidden on mobile */}
      <ul className="hidden md:flex gap-8 list-none m-0 p-0">
        <li>
          <a
            href="#about"
            className="text-sm font-semibold text-noor-muted hover:text-noor-slate transition-colors"
          >
            About
          </a>
        </li>
        <li>
          <a
            href="#services"
            className="text-sm font-semibold text-noor-muted hover:text-noor-slate transition-colors"
          >
            Services
          </a>
        </li>
      </ul>

      {/* CTA — always visible */}
      <a
        href="https://t.me/islam_agent_bot"
        target="_blank"
        rel="noopener noreferrer"
        className="bg-noor-mint text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-emerald-600 transition-colors"
      >
        Open in Telegram →
      </a>
    </nav>
  );
}

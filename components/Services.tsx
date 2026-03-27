type Service = {
  icon: string;
  title: string;
  description: string;
  status: 'live' | 'soon';
  link?: string;
  linkText?: string;
  external?: boolean;
};

const services: Service[] = [
  {
    icon: '📖',
    title: 'Daily Tafsir Bot',
    description:
      'Receive one Quran verse with translation and tafsir at each of your 5 daily prayer times. Start from Al-Fatiha and journey through the entire Quran.',
    status: 'live',
    link: 'https://t.me/islam_agent_bot',
    linkText: 'Start on Telegram →',
    external: true,
  },
  {
    icon: '🔍',
    title: 'Halal Lens',
    description:
      'Scan a food label to instantly check every E-number and ingredient for its halal status.',
    status: 'live',
    link: '/halal-lens',
    linkText: 'Try Halal Lens →',
  },
  {
    icon: '🕌',
    title: 'Prayer Companion',
    description:
      'Smart prayer reminders, qibla direction, and daily dhikr — all in one place.',
    status: 'soon',
  },
];

export default function Services() {
  return (
    <section id="services" className="px-6 md:px-12 py-20">
      <div className="max-w-4xl mx-auto">
        <p className="text-xs font-bold uppercase tracking-widest text-noor-mint mb-3">
          Services
        </p>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-noor-slate mb-3 leading-tight">
          What we&apos;re building
        </h2>
        <p className="text-base md:text-lg text-noor-muted mb-12">
          Tools designed to accompany you through every part of your deen.
        </p>

        {/* Grid: 1 col mobile, 2 col tablet, 3 col desktop */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {services.map((s) => (
            <div
              key={s.title}
              className={`bg-white rounded-2xl p-7 border ${
                s.status === 'live' ? 'border-noor-mint' : 'border-slate-200'
              }`}
            >
              {/* Icon */}
              <div
                className={`w-11 h-11 rounded-xl flex items-center justify-center text-2xl mb-4 ${
                  s.status === 'live' ? 'bg-emerald-50' : 'bg-noor-cloud'
                }`}
              >
                {s.icon}
              </div>

              {/* Text */}
              <h3 className="text-base font-bold text-noor-slate mb-2">{s.title}</h3>
              <p className="text-sm text-noor-muted leading-relaxed mb-5">
                {s.description}
              </p>

              {/* Live: link + badge. Soon: badge only (inert) */}
              {s.status === 'live' ? (
                <>
                  <a
                    href={s.link}
                    {...(s.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                    className="block text-sm font-semibold text-noor-mint hover:text-emerald-600 transition-colors mb-4"
                  >
                    {s.linkText}
                  </a>
                  <span className="inline-block bg-emerald-50 text-noor-mint text-[11px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wide">
                    Live
                  </span>
                </>
              ) : (
                <span className="inline-block bg-noor-cloud text-noor-muted text-[11px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wide">
                  Coming soon
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

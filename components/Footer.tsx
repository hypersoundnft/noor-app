import { Footer } from "@/components/ui/footer";
import { Send } from "lucide-react";

const InstagramIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
    <circle cx="12" cy="12" r="5" />
    <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
  </svg>
);

const NoorLogo = () => (
  <span className="text-xl font-bold tracking-tight text-[#1E293B]">
    noor<span className="text-[#10B981]">.</span>
  </span>
);

export default function SiteFooter() {
  return (
    <Footer
      logo={<NoorLogo />}
      brandName=""
      socialLinks={[
        {
          icon: <Send className="h-5 w-5" />,
          href: "https://t.me/islam_agent_bot",
          label: "Telegram",
        },
        {
          icon: <InstagramIcon />,
          href: "https://www.instagram.com/noor.app_official/",
          label: "Instagram",
        },
      ]}
      mainLinks={[
        { href: "#about", label: "About" },
        { href: "#services", label: "Services" },
        { href: "/halal-lens", label: "Halal Lens" },
        { href: "https://t.me/islam_agent_bot", label: "Telegram Bot" },
        { href: "https://www.instagram.com/noor.app_official/", label: "Instagram" },
      ]}
      legalLinks={[
        { href: "#", label: "Privacy Policy" },
        { href: "#", label: "Terms of Use" },
      ]}
      copyright={{
        text: "© 2026 Noor.",
        license: "Illuminating the permissible.",
      }}
    />
  );
}

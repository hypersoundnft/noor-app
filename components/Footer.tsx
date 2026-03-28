import { Footer } from "@/components/ui/footer";
import { Send } from "lucide-react";

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
      ]}
      mainLinks={[
        { href: "#about", label: "About" },
        { href: "#services", label: "Services" },
        { href: "/halal-lens", label: "Halal Lens" },
        { href: "https://t.me/islam_agent_bot", label: "Telegram Bot" },
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

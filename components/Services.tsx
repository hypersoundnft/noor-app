import { Gallery4 } from "@/components/blocks/gallery4";
import { type Gallery4Item } from "@/components/blocks/gallery4";

const items: Gallery4Item[] = [
  {
    id: "daily-tafsir",
    title: "Daily Tafsir Bot",
    description:
      "Receive one Quran verse with translation and tafsir at each of your 5 daily prayer times. Start from Al-Fatiha and journey through the entire Quran.",
    href: "https://t.me/islam_agent_bot",
    image:
      "https://images.unsplash.com/photo-1519817650390-64a93db51149?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
    badge: "Live",
    badgeColor: "bg-emerald-500/30 text-white",
  },
  {
    id: "halal-lens",
    title: "Halal Lens",
    description:
      "Scan a food label to instantly check every E-number and ingredient for its halal status. Shop with confidence.",
    href: "/halal-lens",
    image:
      "https://images.unsplash.com/photo-1604719312566-8912e9227c6a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
    badge: "Live",
    badgeColor: "bg-emerald-500/30 text-white",
  },
  {
    id: "prayer-companion",
    title: "Prayer Companion",
    description:
      "Smart prayer reminders, qibla direction, and daily dhikr — all in one place.",
    href: "#",
    image:
      "https://images.unsplash.com/photo-1545167496-5e9c4b9b2e6a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
    badge: "Coming Soon",
    badgeColor: "bg-white/20 text-white",
  },
];

export default function Services() {
  return (
    <Gallery4
      title="What we're building"
      description="Tools designed to accompany you through every part of your deen."
      items={items}
    />
  );
}

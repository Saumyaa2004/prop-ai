import { Bot, Building2, Mic, Search, ShieldCheck } from "lucide-react";
import type { OrbitItem } from "@/components/ui/radial-orbital-timeline";

// The hero orbit is a visual menu: each node jumps to a section of this page.
export const sections: OrbitItem[] = [
  {
    id: 1,
    title: "How it works",
    content: "See one plain sentence turn into exact search filters, with the real results.",
    icon: Search,
    href: "#search",
  },
  {
    id: 2,
    title: "Ask Prop AI",
    content: "Chat with the AI assistant. It answers only from real listings in the database.",
    icon: Bot,
    href: "#chat",
  },
  {
    id: 3,
    title: "Voice",
    content: "Tap the mic in the chat to speak, and turn on read-aloud to hear the replies.",
    icon: Mic,
    href: "#chat",
  },
  {
    id: 4,
    title: "Listings",
    content: "Browse every demo listing and filter by budget, locality and bedrooms.",
    icon: Building2,
    href: "#listings",
  },
  {
    id: 5,
    title: "Features",
    content: "What makes the answers trustworthy, and what is live today.",
    icon: ShieldCheck,
    href: "#features",
  },
];

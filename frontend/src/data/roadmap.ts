import { Bot, Building2, CalendarCheck, LayoutDashboard, Mic, Search } from "lucide-react";
import type { TimelineItem } from "@/components/ui/radial-orbital-timeline";

// Keep in sync with docs/PROGRESS.md. Only mark a phase "completed" once it
// is implemented AND tested — this page is public.
export const roadmap: TimelineItem[] = [
  {
    id: 1,
    title: "Property Search",
    date: "Oct 2026",
    content:
      "GET /properties/search: structured SQL filters for locality, budget, bedrooms and amenities. Sale and rent prices never mix.",
    category: "Backend",
    icon: Search,
    relatedIds: [2, 4],
    status: "completed",
    energy: 100,
  },
  {
    id: 2,
    title: "Listing Details",
    date: "Oct 2026",
    content:
      "GET /properties/{code}: full facts for one listing, including sold or rented status, and a clear 404 for unknown codes.",
    category: "Backend",
    icon: Building2,
    relatedIds: [1, 3],
    status: "completed",
    energy: 100,
  },
  {
    id: 3,
    title: "Web Dashboard",
    date: "Phase 2",
    content:
      "React + TypeScript + Vite frontend. Live search, listing details and AI chat are built; CRM views come with Phase 4.",
    category: "Frontend",
    icon: LayoutDashboard,
    relatedIds: [2, 5],
    status: "in-progress",
    energy: 70,
  },
  {
    id: 4,
    title: "AI Agent",
    date: "Oct 2026",
    content:
      "Text chat on Gemini that answers with real listings by calling backend tools. Next: saved conversations and an evaluation set.",
    category: "AI",
    icon: Bot,
    relatedIds: [1, 5, 6],
    status: "in-progress",
    energy: 60,
  },
  {
    id: 5,
    title: "CRM & Booking",
    date: "Phase 4",
    content:
      "Leads, preferences and site-visit booking with confirmation before every write and conflict-safe scheduling.",
    category: "CRM",
    icon: CalendarCheck,
    relatedIds: [3, 4],
    status: "pending",
    energy: 0,
  },
  {
    id: 6,
    title: "Voice",
    date: "Oct 2026",
    content:
      "Speak your search and hear replies read aloud, with typing always available. Booking by voice comes with the CRM.",
    category: "Voice",
    icon: Mic,
    relatedIds: [4],
    status: "completed",
    energy: 100,
  },
];

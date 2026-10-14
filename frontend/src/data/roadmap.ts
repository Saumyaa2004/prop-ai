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
      "React + TypeScript + Vite frontend: listings, filters and CRM views on top of the API.",
    category: "Frontend",
    icon: LayoutDashboard,
    relatedIds: [2, 5],
    status: "in-progress",
    energy: 15,
  },
  {
    id: 4,
    title: "AI Agent",
    date: "Phase 3",
    content:
      "Text chat agent that answers with real listings by calling backend tools. It never invents property facts.",
    category: "AI",
    icon: Bot,
    relatedIds: [1, 5, 6],
    status: "pending",
    energy: 0,
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
    date: "Phase 5",
    content:
      "Speak to search and book, with text always available as a fallback.",
    category: "Voice",
    icon: Mic,
    relatedIds: [4],
    status: "pending",
    energy: 0,
  },
];

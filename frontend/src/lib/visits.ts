/**
 * Prop AI - site visit helpers (pure, no React).
 *
 * Slot times are always shown in India time, where the property is, even if
 * the visitor's browser is set to another timezone.
 */

const TIME_ZONE = "Asia/Kolkata";

// Same rules as the backend's normalise_phone: optional +91 / 91 / 0, then
// 10 digits starting 6-9; spaces and dashes are ignored.
const MOBILE = /^(?:\+?91|0)?[6-9]\d{9}$/;

export function isValidIndianMobile(raw: string): boolean {
  return MOBILE.test(raw.replace(/[\s-]/g, ""));
}

const PARTS = new Intl.DateTimeFormat("en-GB", {
  timeZone: TIME_ZONE,
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** The pieces of a slot in India time; assembled by hand so output is exact. */
function partsOf(iso: string) {
  const parts = Object.fromEntries(
    PARTS.formatToParts(new Date(iso)).map((p) => [p.type, p.value])
  );
  return parts as Record<"weekday" | "day" | "month" | "hour" | "minute", string>;
}

/** "Sun 18 Oct" */
export function formatDay(iso: string): string {
  const p = partsOf(iso);
  return `${p.weekday} ${p.day} ${p.month}`;
}

/** "11:00" */
export function formatTime(iso: string): string {
  const p = partsOf(iso);
  return `${p.hour}:${p.minute}`;
}

/** "Sun 18 Oct, 11:00" — the same label the backend gives the AI. */
export function formatSlot(iso: string): string {
  return `${formatDay(iso)}, ${formatTime(iso)}`;
}

// en-CA writes dates as YYYY-MM-DD.
const DAY_KEY = new Intl.DateTimeFormat("en-CA", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** The India-time date of a slot, "2026-10-18". */
function dayKey(iso: string): string {
  return DAY_KEY.format(new Date(iso));
}

export interface SlotDay {
  day: string;
  label: string;
  slots: string[];
}

/** Slots grouped by India date, keeping the API's order (earliest first). */
export function groupSlotsByDay(slots: string[]): SlotDay[] {
  const groups: SlotDay[] = [];
  for (const slot of slots) {
    const day = dayKey(slot);
    const last = groups.at(-1);
    if (last?.day === day) last.slots.push(slot);
    else groups.push({ day, label: formatDay(slot), slots: [slot] });
  }
  return groups;
}

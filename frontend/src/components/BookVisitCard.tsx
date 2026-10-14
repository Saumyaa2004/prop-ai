import { useId, useState } from "react";
import { CalendarCheck, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/useApi";
import { ApiError, bookVisit, getSlots } from "@/lib/api";
import type { Visit } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  chosenSlot,
  formatSlot,
  formatTime,
  groupSlotsByDay,
  isValidIndianMobile,
} from "@/lib/visits";

// Module level, so useApi's effect doesn't re-run on every render.
// The key is "CODE|n"; bumping n re-loads the slots (after a 409).
const loadSlots = (key: string, signal: AbortSignal) =>
  getSlots(key.split("|")[0], undefined, { signal });

const INPUT =
  "h-10 w-full rounded-lg border border-white/15 bg-black/60 px-3 text-sm text-white outline-none placeholder:text-white/35 focus-visible:border-white/40 focus-visible:ring-2 focus-visible:ring-white/20 aria-[invalid=true]:border-red-400/60";

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "booked"; visit: Visit }
  | { kind: "error"; message: string };

/**
 * Pick a slot, enter name + phone, confirm. The only way a visit gets booked:
 * the AI can propose a slot, but this card (a person's click) does the write.
 */
export default function BookVisitCard({
  listingCode,
  title,
  proposedSlot,
}: {
  listingCode: string;
  title: string;
  /** A slot the AI suggested (ISO). Preselected if it is still free. */
  proposedSlot?: string;
}) {
  const hintId = useId(); // unique even with two cards for one listing
  const [reloads, setReloads] = useState(0);
  const { data, error: loadError, loading } = useApi(`${listingCode}|${reloads}`, loadSlots);
  const slots = data?.slots ?? [];
  const days = groupSlotsByDay(slots);

  const proposalFree = proposedSlot !== undefined && slots.includes(proposedSlot);
  const [picked, setPicked] = useState<string | null>(null);
  const [proposalDismissed, setProposalDismissed] = useState(false);
  const slot = chosenSlot({ picked, proposedSlot, proposalDismissed, slots });
  const [pickedDay, setPickedDay] = useState<string | null>(null);
  const day =
    days.find((d) => d.day === pickedDay) ??
    days.find((d) => slot !== null && d.slots.includes(slot)) ??
    days[0];

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const phoneInvalid = phone.trim() !== "" && !isValidIndianMobile(phone);
  const ready =
    slot !== null && name.trim().length >= 2 && isValidIndianMobile(phone) && status.kind !== "submitting";

  const confirm = async () => {
    if (!ready || slot === null) return;
    setStatus({ kind: "submitting" });
    try {
      const visit = await bookVisit({ listing_code: listingCode, starts_at: slot, name: name.trim(), phone });
      setStatus({ kind: "booked", visit });
    } catch (caught) {
      const apiError = caught instanceof ApiError ? caught : new ApiError(0, "Unexpected error.");
      // Taken, passed or failed: show fresh slots and make the user pick again,
      // never falling back to the AI's proposal behind their back.
      setPicked(null);
      setProposalDismissed(true);
      setReloads((n) => n + 1);
      setStatus({
        kind: "error",
        message: apiError.status === 0 ? "Can't reach the Prop AI API. Is the backend running?" : apiError.message,
      });
    }
  };

  if (status.kind === "booked") {
    return (
      <div
        role="status"
        className="flex items-start gap-3 rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-sm text-emerald-100"
      >
        <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-300" aria-hidden="true" />
        <div>
          <p className="font-medium">Visit booked</p>
          <p className="mt-0.5 text-emerald-100/80">
            {status.visit.title} · {formatSlot(status.visit.starts_at)} (India time)
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-xl border border-white/15 bg-white/[0.04] p-4">
      <div className="flex items-center gap-2">
        <CalendarCheck className="size-4 text-teal-300" aria-hidden="true" />
        <p className="text-sm font-medium text-white">Book a visit · {title}</p>
      </div>

      {loading && (
        <p className="flex items-center gap-2 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          Loading free times…
        </p>
      )}
      {loadError && (
        <p role="alert" className="text-sm text-red-200">
          {loadError.status === 0 ? "Can't reach the Prop AI API. Is the backend running?" : loadError.message}
        </p>
      )}

      {data && (
        <>
          {proposedSlot && !proposalFree && !proposalDismissed && (
            <p className="text-sm text-amber-200">
              {formatSlot(proposedSlot)} is no longer free. Please pick another time.
            </p>
          )}
          {days.length === 0 ? (
            <p className="text-sm text-white/60">No free times in the next 14 days.</p>
          ) : (
            <fieldset className="space-y-2">
              <legend className="mb-2 text-xs text-white/50">Pick a time (India time)</legend>
              <div className="flex gap-1.5 overflow-x-auto pb-1">
                {days.map((d) => (
                  <button
                    key={d.day}
                    type="button"
                    aria-pressed={d.day === day?.day}
                    onClick={() => {
                      setPickedDay(d.day);
                      setStatus({ kind: "idle" }); // a new choice clears the old error
                    }}
                    className={cn(
                      "shrink-0 rounded-full border px-3 py-1 text-xs transition-colors",
                      d.day === day?.day
                        ? "border-white bg-white text-black"
                        : "border-white/15 text-white/70 hover:border-white/30"
                    )}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {day?.slots.map((s) => (
                  <button
                    key={s}
                    type="button"
                    aria-pressed={s === slot}
                    aria-label={formatSlot(s)}
                    onClick={() => {
                      setPicked(s);
                      setStatus({ kind: "idle" });
                    }}
                    className={cn(
                      "rounded-lg border px-3 py-1.5 text-sm tabular-nums transition-colors",
                      s === slot
                        ? "border-teal-300 bg-teal-300/15 text-teal-100"
                        : "border-white/15 text-white/80 hover:border-white/30"
                    )}
                  >
                    {formatTime(s)}
                  </button>
                ))}
              </div>
            </fieldset>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-xs text-white/60">
              <span>Name</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                autoComplete="off" // public site: don't autofill a real name
                placeholder="e.g. Asha Sharma"
                className={INPUT}
              />
            </label>
            <label className="space-y-1 text-xs text-white/60">
              <span>Mobile number</span>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                type="tel"
                inputMode="tel"
                maxLength={20}
                autoComplete="off" // public site: don't autofill a real number
                placeholder="e.g. 98765 43210"
                aria-invalid={phoneInvalid}
                aria-describedby={hintId}
                className={INPUT}
              />
              <span id={hintId} className={phoneInvalid ? "text-red-200" : "text-white/40"}>
                10-digit Indian mobile number
              </span>
            </label>
          </div>

          {status.kind === "error" && (
            <p role="alert" className="text-sm text-red-200">
              {status.message}
            </p>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-white/40">Portfolio project: please use a made-up name and number.</p>
            <Button onClick={confirm} disabled={!ready} className="gap-1.5">
              {status.kind === "submitting" && <Loader2 className="animate-spin" aria-hidden="true" />}
              {slot ? `Confirm ${formatSlot(slot)}` : "Confirm visit"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

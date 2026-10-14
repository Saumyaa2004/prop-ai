import { describe, expect, it } from "vitest";
import {
  chosenSlot,
  formatDay,
  formatSlot,
  formatTime,
  groupSlotsByDay,
  isValidIndianMobile,
} from "@/lib/visits";

describe("isValidIndianMobile", () => {
  it("accepts the formats people type (same rules as the backend)", () => {
    for (const raw of ["98765 43210", "+91-98765-43210", "09876543210", "919876543210"]) {
      expect(isValidIndianMobile(raw)).toBe(true);
    }
  });

  it("rejects anything that isn't an Indian mobile", () => {
    for (const raw of ["12345 67890", "98765", "abc", ""]) {
      expect(isValidIndianMobile(raw)).toBe(false);
    }
  });
});

describe("slot formatting", () => {
  it("shows slots the way the backend labels them", () => {
    expect(formatSlot("2026-10-18T11:00:00+05:30")).toBe("Sun 18 Oct, 11:00");
    expect(formatSlot("2026-11-08T10:00:00+05:30")).toBe("Sun 8 Nov, 10:00");
  });

  it("always uses India time, whatever the visitor's timezone", () => {
    // 05:30 UTC is 11:00 in India; a London browser must still say 11:00.
    expect(formatSlot("2026-10-18T05:30:00Z")).toBe("Sun 18 Oct, 11:00");
    expect(formatTime("2026-10-18T05:30:00Z")).toBe("11:00");
    expect(formatDay("2026-10-18T05:30:00Z")).toBe("Sun 18 Oct");
  });
});

describe("groupSlotsByDay", () => {
  it("groups slots by their India date, in order", () => {
    const groups = groupSlotsByDay([
      "2026-10-18T10:00:00+05:30",
      "2026-10-18T11:00:00+05:30",
      "2026-10-19T10:00:00+05:30",
    ]);

    expect(groups.map((g) => g.day)).toEqual(["2026-10-18", "2026-10-19"]);
    expect(groups[0].label).toBe("Sun 18 Oct");
    expect(groups[0].slots).toHaveLength(2);
  });

  it("returns nothing for no slots", () => {
    expect(groupSlotsByDay([])).toEqual([]);
  });
});

describe("test setup", () => {
  it("runs outside India time, so the IST tests above mean something", () => {
    expect(new Date("2026-10-18T11:00:00+05:30").getHours()).not.toBe(11);
  });
});

describe("chosenSlot", () => {
  const slots = ["2026-10-15T11:00:00+05:30", "2026-10-15T15:00:00+05:30"];
  const proposedSlot = slots[0];

  it("preselects the AI's proposal while it is free", () => {
    expect(chosenSlot({ picked: null, proposedSlot, proposalDismissed: false, slots })).toBe(slots[0]);
  });

  it("prefers what the user picked", () => {
    expect(chosenSlot({ picked: slots[1], proposedSlot, proposalDismissed: false, slots })).toBe(slots[1]);
  });

  it("never falls back to the proposal after a booking error", () => {
    // The user's pick failed: Confirm must not silently switch to the AI's time.
    expect(chosenSlot({ picked: null, proposedSlot, proposalDismissed: true, slots })).toBeNull();
  });

  it("drops a pick that is no longer offered (taken or passed)", () => {
    expect(chosenSlot({ picked: "2026-10-15T10:00:00+05:30", slots, proposalDismissed: false })).toBeNull();
  });

  it("ignores a proposal that is no longer free", () => {
    expect(chosenSlot({ picked: null, proposedSlot: "2026-10-15T10:00:00+05:30", proposalDismissed: false, slots })).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import { formatPrice, humanize } from "@/lib/format";

describe("formatPrice", () => {
  it("shows sale prices in crore", () => {
    expect(formatPrice(13_800_000, "sale")).toBe("₹1.38 Cr");
    expect(formatPrice(125_000_000, "sale")).toBe("₹12.5 Cr");
    expect(formatPrice(20_000_000, "sale")).toBe("₹2 Cr");
  });

  it("shows sale prices under a crore in lakh", () => {
    expect(formatPrice(9_800_000, "sale")).toBe("₹98 L");
  });

  it("shows rent as a monthly amount with Indian digit grouping", () => {
    expect(formatPrice(42_000, "rent")).toBe("₹42,000/mo");
    expect(formatPrice(125_000, "rent")).toBe("₹1,25,000/mo");
  });

  it("never shows a monthly rent in crore, even if it is large", () => {
    expect(formatPrice(12_000_000, "rent")).toBe("₹1,20,00,000/mo");
  });
});

describe("humanize", () => {
  it("turns API codes into labels", () => {
    expect(humanize("power_backup")).toBe("Power backup");
    expect(humanize("semi_furnished")).toBe("Semi furnished");
  });
});

import { describe, expect, it } from "vitest";
import { listingFromUrl, withListing } from "@/lib/url";

describe("listingFromUrl", () => {
  it("reads the listing code", () => {
    expect(listingFromUrl("https://propai.dev/?listing=PAI-DEMO-002")).toBe("PAI-DEMO-002");
  });

  it("returns null when there is no listing or it is blank", () => {
    expect(listingFromUrl("https://propai.dev/")).toBeNull();
    expect(listingFromUrl("https://propai.dev/?listing=%20")).toBeNull();
  });
});

describe("withListing", () => {
  it("adds the listing and drops the section anchor", () => {
    expect(withListing("https://propai.dev/#listings", "PAI-DEMO-002")).toBe(
      "https://propai.dev/?listing=PAI-DEMO-002"
    );
  });

  it("removes the listing but keeps other parameters", () => {
    expect(withListing("https://propai.dev/?listing=PAI-DEMO-002&utm=x", null)).toBe(
      "https://propai.dev/?utm=x"
    );
  });

  it("encodes unusual input instead of breaking the URL", () => {
    expect(withListing("https://propai.dev/", "a&b=c")).toBe(
      "https://propai.dev/?listing=a%26b%3Dc"
    );
  });
});

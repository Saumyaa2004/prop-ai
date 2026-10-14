import { describe, expect, it } from "vitest";
import { sections } from "@/data/sections";

// The page's section ids (App.tsx, ChatSection, ListingsSection).
const PAGE_SECTIONS = ["#search", "#chat", "#listings", "#features"];

describe("orbit sections", () => {
  it("links every node to a section that exists on the page", () => {
    for (const section of sections) {
      expect(PAGE_SECTIONS).toContain(section.href);
    }
  });

  it("gives every node a unique id and a description", () => {
    expect(new Set(sections.map((s) => s.id)).size).toBe(sections.length);
    for (const section of sections) {
      expect(section.content.trim()).not.toBe("");
    }
  });
});

import { describe, expect, it } from "vitest";
import type { Property } from "@/lib/api";
import { MAX_HISTORY, cleanReply, toApiHistory } from "@/lib/chat";
import type { ConversationMessage } from "@/lib/chat";

describe("toApiHistory", () => {
  it("sends only role and content", () => {
    const messages: ConversationMessage[] = [
      { role: "user", content: "flats in Powai" },
      { role: "assistant", content: "Here you go", listings: [{} as Property] },
    ];

    expect(toApiHistory(messages)).toEqual([
      { role: "user", content: "flats in Powai" },
      { role: "assistant", content: "Here you go" },
    ]);
  });

  it("keeps only the newest messages the backend accepts", () => {
    const messages: ConversationMessage[] = Array.from({ length: 25 }, (_, i) => ({
      role: i % 2 === 0 ? "user" : "assistant",
      content: `m${i}`,
    }));

    const history = toApiHistory(messages);

    expect(history).toHaveLength(MAX_HISTORY);
    expect(history.at(-1)?.content).toBe("m24");
  });
});

describe("cleanReply", () => {
  it("removes markdown emphasis and headings", () => {
    expect(cleanReply("## Results\nI found **two** flats")).toBe("Results\nI found two flats");
  });

  it("turns markdown bullets into plain bullets", () => {
    expect(cleanReply("Options:\n* PAI-DEMO-002\n- PAI-DEMO-001")).toBe(
      "Options:\n• PAI-DEMO-002\n• PAI-DEMO-001"
    );
  });

  it("leaves plain text alone", () => {
    expect(cleanReply("Are you looking to buy or rent?")).toBe("Are you looking to buy or rent?");
  });
});

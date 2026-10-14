import { describe, expect, it } from "vitest";
import { SPEECH_MAX_CHARS, textForSpeech, voiceErrorMessage } from "@/lib/voice/speechText";

describe("textForSpeech", () => {
  it("reads price labels the way people say them", () => {
    expect(textForSpeech("It costs ₹1.38 Cr.")).toBe("It costs 1.38 crore rupees.");
    expect(textForSpeech("Only ₹98 L.")).toBe("Only 98 lakh rupees.");
    expect(textForSpeech("Rent is ₹42,000/mo.")).toBe("Rent is 42,000 rupees a month.");
    expect(textForSpeech("Rent is ₹1,25,000/month.")).toBe("Rent is 1,25,000 rupees a month.");
  });

  it("says listing codes as demo listing numbers", () => {
    expect(textForSpeech("See PAI-DEMO-002.")).toBe("See demo listing 2.");
  });

  it("drops bullets and joins lines into sentences", () => {
    expect(textForSpeech("Options:\n• A\n• B")).toBe("Options: A. B.");
  });

  it("caps long replies at a sentence boundary", () => {
    const long = "This is a sentence. ".repeat(60);
    const spoken = textForSpeech(long);
    expect(spoken.length).toBeLessThanOrEqual(SPEECH_MAX_CHARS);
    expect(spoken.endsWith(".")).toBe(true);
  });
});

describe("voiceErrorMessage", () => {
  it("explains blocked microphone access", () => {
    expect(voiceErrorMessage("not-allowed")).toBe(
      "Microphone access is blocked. Allow it in your browser's address bar, or type instead."
    );
  });

  it("asks again when nothing was heard", () => {
    expect(voiceErrorMessage("no-speech")).toBe("I didn't catch that. Tap the mic and try again.");
  });

  it("explains the network requirement", () => {
    expect(voiceErrorMessage("network")).toBe(
      "Voice input needs an internet connection. You can type instead."
    );
  });

  it("stays silent for a user-cancelled recognition", () => {
    expect(voiceErrorMessage("aborted")).toBeNull();
  });

  it("has a fallback for anything else", () => {
    expect(voiceErrorMessage("audio-capture")).toBe("Voice input didn't work. You can type instead.");
  });
});

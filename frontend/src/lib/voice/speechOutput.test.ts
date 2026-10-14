import { describe, expect, it } from "vitest";
import { createSpeechOutput, pickVoice } from "@/lib/voice/speechOutput";
import type { SynthWindow } from "@/lib/voice/speechOutput";

function voice(lang: string): SpeechSynthesisVoice {
  return { lang, name: `voice-${lang}`, default: false, localService: true, voiceURI: lang };
}

const enIN = voice("en-IN");
const enUS = voice("en-US");
const hiIN = voice("hi-IN");

/** Records what the browser would have been asked to do. */
class FakeUtterance {
  static last: FakeUtterance | null = null;
  lang = "";
  voice: SpeechSynthesisVoice | null = null;
  onend: (() => void) | null = null;
  text: string;

  constructor(text: string) {
    this.text = text;
    FakeUtterance.last = this;
  }
}

function fakeWindow(voices: SpeechSynthesisVoice[] = [enUS, enIN]) {
  const log: string[] = [];
  const win: SynthWindow = {
    speechSynthesis: {
      speak: (u) => log.push(`speak:${(u as unknown as FakeUtterance).text}`),
      cancel: () => log.push("cancel"),
      getVoices: () => voices,
    },
    // The fake implements only what our adapter uses, hence the cast.
    SpeechSynthesisUtterance: FakeUtterance as unknown as SynthWindow["SpeechSynthesisUtterance"],
  };
  return { win, log };
}

function output(win: SynthWindow) {
  const speech = createSpeechOutput(win);
  if (!speech) throw new Error("expected speech output to be supported");
  return speech;
}

describe("createSpeechOutput", () => {
  it("returns null without speechSynthesis", () => {
    expect(createSpeechOutput({})).toBeNull();
  });

  it("prefers an en-IN voice, then any English voice, then none", () => {
    expect(pickVoice([enUS, enIN])).toBe(enIN);
    expect(pickVoice([enUS, hiIN])).toBe(enUS);
    expect(pickVoice([hiIN])).toBeNull();
    expect(pickVoice([])).toBeNull();
  });

  it("cancels anything already speaking before speaking", () => {
    const { win, log } = fakeWindow();
    const speech = output(win);

    speech.speak("a");
    speech.speak("b");

    expect(log).toEqual(["cancel", "speak:a", "cancel", "speak:b"]);
  });

  it("speaks with lang en-IN and the picked voice, and calls onEnd", () => {
    const { win } = fakeWindow();
    let ended = 0;

    output(win).speak("hello", () => ended++);
    FakeUtterance.last?.onend?.();

    expect(FakeUtterance.last?.lang).toBe("en-IN");
    expect(FakeUtterance.last?.voice).toBe(enIN);
    expect(ended).toBe(1);
  });

  it("does not speak empty text", () => {
    const { win, log } = fakeWindow();

    output(win).speak("   ");

    expect(log.some((entry) => entry.startsWith("speak:"))).toBe(false);
  });

  it("cancel() stops speech", () => {
    const { win, log } = fakeWindow();

    output(win).cancel();

    expect(log.at(-1)).toBe("cancel");
  });
});

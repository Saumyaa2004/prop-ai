import { beforeEach, describe, expect, it } from "vitest";
import { createSpeechInput } from "@/lib/voice/speechInput";
import type { SpeechInputHandlers } from "@/lib/voice/speechInput";

type ResultList = ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;

/** Stands in for the browser's SpeechRecognition; tests drive its events. */
class FakeRecognition {
  static instances: FakeRecognition[] = [];
  lang = "";
  interimResults = false;
  continuous = true;
  maxAlternatives = 0;
  startCalls = 0;
  stopCalls = 0;
  onresult: ((event: { resultIndex: number; results: ResultList }) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;

  constructor() {
    FakeRecognition.instances.push(this);
  }
  start() {
    this.startCalls++;
  }
  stop() {
    this.stopCalls++;
  }
  abort() {}

  emitResult(transcript: string, isFinal: boolean) {
    this.onresult?.({ resultIndex: 0, results: [{ isFinal, 0: { transcript } }] });
  }
  emitError(code: string) {
    this.onerror?.({ error: code });
  }
  emitEnd() {
    this.onend?.();
  }
}

function recordingHandlers(log: string[]): SpeechInputHandlers {
  return {
    onInterim: (text) => log.push(`interim:${text}`),
    onFinal: (text) => log.push(`final:${text}`),
    onError: (code) => log.push(`error:${code}`),
    onEnd: () => log.push("end"),
  };
}

function startListening(log: string[]) {
  const input = createSpeechInput({ webkitSpeechRecognition: FakeRecognition });
  if (!input) throw new Error("expected speech input to be supported");
  input.start(recordingHandlers(log));
  return { input, recognition: FakeRecognition.instances.at(-1)! };
}

beforeEach(() => {
  FakeRecognition.instances = [];
});

describe("createSpeechInput", () => {
  it("returns null when the browser has no speech recognition", () => {
    expect(createSpeechInput({})).toBeNull();
  });

  it("prefers the standard constructor, falls back to webkit", () => {
    expect(createSpeechInput({ webkitSpeechRecognition: FakeRecognition })).not.toBeNull();
  });

  it("configures Indian English, single utterance, interim results", () => {
    const { recognition } = startListening([]);

    expect(recognition.lang).toBe("en-IN");
    expect(recognition.interimResults).toBe(true);
    expect(recognition.continuous).toBe(false);
    expect(recognition.maxAlternatives).toBe(1);
    expect(recognition.startCalls).toBe(1);
  });

  it("reports interim then final transcript, then end", () => {
    const log: string[] = [];
    const { recognition } = startListening(log);

    recognition.emitResult("studio in", false);
    recognition.emitResult("studio in Powai", true);
    recognition.emitEnd();

    expect(log).toEqual(["interim:studio in", "final:studio in Powai", "end"]);
  });

  it("reports a blocked microphone as an error followed by end", () => {
    const log: string[] = [];
    const { recognition } = startListening(log);

    recognition.emitError("not-allowed");
    recognition.emitEnd();

    expect(log).toEqual(["error:not-allowed", "end"]);
  });

  it("ends without a final result when nothing was said", () => {
    const log: string[] = [];
    const { recognition } = startListening(log);

    recognition.emitEnd();

    expect(log).toEqual(["end"]);
  });

  it("trims the final transcript and ignores empty ones", () => {
    const log: string[] = [];
    const { recognition } = startListening(log);

    recognition.emitResult("  rent in Powai ", true);
    recognition.emitResult("   ", true);

    expect(log).toEqual(["final:rent in Powai"]);
  });

  it("stop() stops the active recognition", () => {
    const { input, recognition } = startListening([]);

    input.stop();

    expect(recognition.stopCalls).toBe(1);
  });
});

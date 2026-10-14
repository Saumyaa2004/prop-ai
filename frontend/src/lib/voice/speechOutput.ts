/**
 * Prop AI - text-to-speech adapter.
 *
 * Wraps the browser's speechSynthesis. Receives the window object as a
 * parameter so tests can pass a fake synthesizer.
 */

export type SynthWindow = {
  speechSynthesis?: Pick<SpeechSynthesis, "speak" | "cancel" | "getVoices">;
  SpeechSynthesisUtterance?: new (text: string) => SpeechSynthesisUtterance;
};

export interface SpeechOutput {
  speak(text: string, onEnd?: () => void): void;
  cancel(): void;
}

const LANG = "en-IN";

/** Best voice for Indian English: exact match, then any English voice, else none. */
export function pickVoice(
  voices: SpeechSynthesisVoice[],
  preferred: string = LANG
): SpeechSynthesisVoice | null {
  // Android reports "en_IN"; normalise before comparing.
  const lang = (v: SpeechSynthesisVoice) => v.lang.replace("_", "-").toLowerCase();
  return (
    voices.find((v) => lang(v) === preferred.toLowerCase()) ??
    voices.find((v) => lang(v).startsWith("en")) ??
    null
  );
}

/** Speech output for this browser, or null if it can't speak. */
export function createSpeechOutput(win: SynthWindow): SpeechOutput | null {
  const synth = win.speechSynthesis;
  const Utterance = win.SpeechSynthesisUtterance;
  if (!synth || !Utterance) return null;

  return {
    speak(text, onEnd) {
      if (!text.trim()) return;
      // speak() queues; cancel first so a new reply never waits behind an old one.
      synth.cancel();
      const utterance = new Utterance(text);
      utterance.lang = LANG;
      // Chrome loads voices asynchronously, so pick at speak time, not at creation.
      const voice = pickVoice(synth.getVoices());
      if (voice) utterance.voice = voice;
      utterance.onend = () => onEnd?.();
      synth.speak(utterance);
    },
    cancel() {
      synth.cancel();
    },
  };
}

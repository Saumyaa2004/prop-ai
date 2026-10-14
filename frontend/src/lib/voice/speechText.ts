/**
 * Prop AI - turning chat text into something pleasant to hear.
 *
 * Screens show "₹1.38 Cr" and "PAI-DEMO-002"; a speech engine would read
 * those as symbols and letters. These pure helpers rewrite them the way a
 * person would say them, and turn recognition error codes into plain advice.
 */

/** Long replies are cut (at a sentence end) so read-aloud never drones on. */
export const SPEECH_MAX_CHARS = 600;

const NUMBER = String.raw`(\d[\d,]*(?:\.\d+)?)`;

/** A chat reply rewritten for text-to-speech. */
export function textForSpeech(reply: string): string {
  const spoken = reply
    // Order matters: specific price forms before the general ₹ rule.
    .replace(new RegExp(String.raw`₹\s?${NUMBER}\s?Cr\b`, "g"), "$1 crore rupees")
    .replace(new RegExp(String.raw`₹\s?${NUMBER}\s?L\b`, "g"), "$1 lakh rupees")
    .replace(new RegExp(String.raw`₹\s?${NUMBER}\s?/\s?(?:month|mo)\b`, "g"), "$1 rupees a month")
    .replace(new RegExp(String.raw`₹\s?${NUMBER}`, "g"), "$1 rupees")
    .replace(/PAI-DEMO-0*(\d+)/gi, "demo listing $1")
    .split("\n")
    .map((line) => line.replace(/^\s*[•*-]\s*/, "").trim())
    .filter(Boolean)
    .map((line) => (/[.?!:]$/.test(line) ? line : `${line}.`))
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();

  return capAtSentence(spoken, SPEECH_MAX_CHARS);
}

function capAtSentence(text: string, max: number): string {
  if (text.length <= max) return text;
  const head = text.slice(0, max);
  const lastEnd = Math.max(head.lastIndexOf("."), head.lastIndexOf("?"), head.lastIndexOf("!"));
  return lastEnd > 0 ? head.slice(0, lastEnd + 1) : head;
}

/** Plain advice for a speech-recognition error code; null = say nothing. */
export function voiceErrorMessage(code: string): string | null {
  switch (code) {
    case "aborted":
      return null; // the user (or our code) cancelled on purpose
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone access is blocked. Allow it in your browser's address bar, or type instead.";
    case "no-speech":
      return "I didn't catch that. Tap the mic and try again.";
    case "network":
      return "Voice input needs an internet connection. You can type instead.";
    default:
      return "Voice input didn't work. You can type instead.";
  }
}

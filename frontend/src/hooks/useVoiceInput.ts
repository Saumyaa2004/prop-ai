import { useEffect, useRef, useState } from "react";
import { createSpeechInput } from "@/lib/voice/speechInput";
import type { SpeechInput, SpeechWindow } from "@/lib/voice/speechInput";
import { voiceErrorMessage } from "@/lib/voice/speechText";

export const VOICE_UNSUPPORTED_HINT = "Voice input isn't supported in this browser. Type instead.";

// window has none of SpeechWindow's (optional) members in TS's DOM lib, so a
// direct pass fails the weak-type check (TS2559); the cast is deliberate.
const speechWindow = () => window as unknown as SpeechWindow;

/** Mic state for the chat. `onFinal` receives what the user said. */
export function useVoiceInput(onFinal: (text: string) => void) {
  const [supported] = useState(() => {
    const win = speechWindow();
    return Boolean(win.SpeechRecognition ?? win.webkitSpeechRecognition);
  });
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Created on first use, not at render: most visitors never tap the mic.
  const inputRef = useRef<SpeechInput | null>(null);

  // Recognition answers seconds later; always call the latest callback, not
  // one captured by an old render.
  const onFinalRef = useRef(onFinal);
  useEffect(() => {
    onFinalRef.current = onFinal;
  });

  // Never keep the mic open after the chat disappears.
  useEffect(() => () => inputRef.current?.stop(), []);

  const start = () => {
    if (listening) return;
    inputRef.current ??= createSpeechInput(speechWindow());
    const input = inputRef.current;
    if (!input) {
      setError(VOICE_UNSUPPORTED_HINT);
      return;
    }
    setError(null);
    setInterim("");
    setListening(true);
    try {
      input.start({
        onInterim: setInterim,
        onFinal: (text) => {
          setInterim("");
          onFinalRef.current(text);
        },
        onError: (code) => setError(voiceErrorMessage(code)),
        onEnd: () => {
          setListening(false);
          setInterim("");
        },
      });
    } catch {
      // e.g. start() while the browser still holds the previous session
      setListening(false);
      setError(voiceErrorMessage("unknown"));
    }
  };

  const stop = () => inputRef.current?.stop();

  return { supported, listening, interim, error, start, stop };
}

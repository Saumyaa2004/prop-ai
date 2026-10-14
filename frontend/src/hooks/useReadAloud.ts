import { useEffect, useState } from "react";
import { createSpeechOutput } from "@/lib/voice/speechOutput";

const STORAGE_KEY = "propai.readAloud";

// Storage can be unavailable (private mode, blocked site data): never let a
// convenience setting break the chat.
function readPreference(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "on";
  } catch {
    return false;
  }
}

function savePreference(enabled: boolean) {
  try {
    window.localStorage.setItem(STORAGE_KEY, enabled ? "on" : "off");
  } catch {
    // ignore: the toggle still works for this visit
  }
}

/** "Read replies aloud": off by default, remembered per browser. */
export function useReadAloud() {
  const [output] = useState(() => createSpeechOutput(window));
  const [enabled, setEnabled] = useState(readPreference);

  // Stop talking if the chat disappears.
  useEffect(() => () => output?.cancel(), [output]);

  const toggle = () => {
    const next = !enabled;
    setEnabled(next);
    savePreference(next);
    if (!next) output?.cancel();
  };

  return {
    supported: output !== null,
    enabled,
    toggle,
    speak: (text: string) => output?.speak(text),
    cancel: () => output?.cancel(),
  };
}

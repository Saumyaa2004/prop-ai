/**
 * Prop AI - speech-to-text adapter.
 *
 * Wraps the browser's Web Speech API (SpeechRecognition, or the prefixed
 * webkitSpeechRecognition) behind four simple callbacks. It receives the
 * window object as a parameter, so tests can pass a fake recognizer.
 */

type ResultList = ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;

/** The parts of SpeechRecognition we use (TypeScript's DOM lib doesn't declare it). */
interface RecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: { resultIndex: number; results: ResultList }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
}

type RecognitionConstructor = new () => RecognitionLike;

export type SpeechWindow = {
  SpeechRecognition?: RecognitionConstructor;
  webkitSpeechRecognition?: RecognitionConstructor;
};

export interface SpeechInputHandlers {
  onInterim: (text: string) => void;
  onFinal: (text: string) => void;
  onError: (code: string) => void; // SpeechRecognitionErrorCode values
  onEnd: () => void; // always called last, exactly once per start()
}

export interface SpeechInput {
  start(handlers: SpeechInputHandlers): void;
  stop(): void;
}

/** A speech input for this browser, or null if it has no speech recognition. */
export function createSpeechInput(win: SpeechWindow): SpeechInput | null {
  const Recognition = win.SpeechRecognition ?? win.webkitSpeechRecognition;
  if (!Recognition) return null;

  let active: RecognitionLike | null = null;

  return {
    start(handlers) {
      const recognition = new Recognition();
      recognition.lang = "en-IN"; // Indian English: localities, lakh, crore
      recognition.interimResults = true; // show words while the user speaks
      recognition.continuous = false; // one utterance, then stop
      recognition.maxAlternatives = 1;

      let ended = false;
      recognition.onresult = (event) => {
        let transcript = "";
        let isFinal = false;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
          isFinal ||= event.results[i].isFinal;
        }
        const text = transcript.trim();
        if (!text) return;
        if (isFinal) handlers.onFinal(text);
        else handlers.onInterim(text);
      };
      recognition.onerror = (event) => handlers.onError(event.error);
      recognition.onend = () => {
        if (ended) return; // the UI relies on exactly one end per start
        ended = true;
        active = null;
        handlers.onEnd();
      };

      active = recognition;
      recognition.start();
    },
    stop() {
      active?.stop();
    },
  };
}

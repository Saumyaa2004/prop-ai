import { useEffect, useRef, useState } from "react";
import {
  Bot,
  MessageSquarePlus,
  Mic,
  MicOff,
  RotateCcw,
  SendHorizontal,
  Sparkles,
  Volume2,
  VolumeX,
} from "lucide-react";
import BookVisitCard from "@/components/BookVisitCard";
import ListingCard from "@/components/ListingCard";
import { Button } from "@/components/ui/button";
import { MAX_MESSAGE_LENGTH, useChat } from "@/hooks/useChat";
import { useReadAloud } from "@/hooks/useReadAloud";
import { VOICE_UNSUPPORTED_HINT, useVoiceInput } from "@/hooks/useVoiceInput";
import { cn } from "@/lib/utils";
import { textForSpeech } from "@/lib/voice/speechText";

const EXAMPLES = [
  "2BHK in Powai under 1.5 crore with parking",
  "A furnished studio to rent in Powai",
  "Something in Andheri West",
];

function ThinkingIndicator() {
  return (
    <div className="flex w-fit items-center gap-1.5 rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-3">
      <span className="sr-only">Prop AI is thinking…</span>
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          aria-hidden="true"
          className="size-1.5 rounded-full bg-white/60 motion-safe:animate-bounce"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}

export default function ChatSection({
  onOpenListing,
}: {
  onOpenListing: (code: string, button: HTMLButtonElement) => void;
}) {
  const { messages, sending, error, send, retry, reset } = useChat();
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  // Keep the newest message in view (instantly if the user prefers less motion).
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    list.scrollTo({ top: list.scrollHeight, behavior: reduce ? "auto" : "smooth" });
  }, [messages.length, sending, error]);

  const readAloud = useReadAloud();

  const submit = (text: string) => {
    if (!text.trim() || sending) return;
    readAloud.cancel(); // a new question makes the old answer irrelevant
    send(text);
    setInput("");
  };

  // Voice: what the user said is sent as soon as recognition is final.
  const voice = useVoiceInput((text) => submit(text));

  const toggleMic = () => {
    if (voice.listening) {
      voice.stop();
      return;
    }
    readAloud.cancel(); // don't let the mic hear the assistant talking
    voice.start();
  };

  const newChat = () => {
    readAloud.cancel();
    reset();
  };

  // Read each new assistant reply aloud once. The ref remembers how many
  // messages were already handled, so re-renders never repeat speech.
  const handledRef = useRef(messages.length);
  useEffect(() => {
    const last = messages.at(-1);
    if (messages.length > handledRef.current && last?.role === "assistant" && readAloud.enabled) {
      readAloud.speak(textForSpeech(last.content));
    }
    handledRef.current = messages.length;
  }, [messages, readAloud]);

  return (
    <section id="chat" className="mx-auto max-w-6xl scroll-mt-20 px-4 pb-24 sm:px-6">
      <div className="mb-8 max-w-2xl">
        <p className="mb-3 text-sm font-medium tracking-wider text-purple-300 uppercase">
          AI assistant
        </p>
        <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          Ask Prop AI
        </h2>
        <p className="mt-4 text-white/60">
          Describe what you want in plain words. The assistant searches the same live
          listings as the filters below, and asks when something is unclear.
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02]">
        <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 via-blue-500 to-teal-500">
              <Bot className="size-4 text-white" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-medium text-white">Prop AI assistant</p>
              <p className="text-xs text-white/45">Gemini · fictional demo listings</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {readAloud.supported && (
              <Button
                variant="ghost"
                size="sm"
                onClick={readAloud.toggle}
                aria-pressed={readAloud.enabled}
                className={cn("gap-1.5", readAloud.enabled ? "text-white" : "text-white/60")}
              >
                {readAloud.enabled ? <Volume2 aria-hidden="true" /> : <VolumeX aria-hidden="true" />}
                <span className="hidden sm:inline">Read replies aloud</span>
                <span className="sr-only sm:hidden">Read replies aloud</span>
              </Button>
            )}
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={newChat} className="gap-1.5 text-white/70">
                <MessageSquarePlus aria-hidden="true" />
                New chat
              </Button>
            )}
          </div>
        </div>

        <div
          ref={listRef}
          role="log"
          aria-label="Conversation with Prop AI"
          className="h-[30rem] space-y-4 overflow-y-auto p-4 sm:h-[34rem] sm:p-6"
        >
          {messages.length === 0 && !sending && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <Sparkles className="mb-3 size-8 text-purple-300" aria-hidden="true" />
              <p className="font-medium text-white">Try asking</p>
              <div className="mt-4 flex max-w-xl flex-wrap justify-center gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => submit(example)}
                    disabled={voice.listening}
                    className="rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5 text-sm text-white/80 transition-colors hover:border-white/30 hover:text-white focus-visible:ring-2 focus-visible:ring-white/30 focus-visible:outline-none"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className="space-y-3">
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
                  message.role === "user"
                    ? "ml-auto w-fit rounded-br-sm bg-white text-black"
                    : "w-fit rounded-bl-sm border border-white/10 bg-white/[0.06] text-white/90"
                )}
              >
                <span className="sr-only">{message.role === "user" ? "You: " : "Prop AI: "}</span>
                {message.content}
              </div>
              {message.listings && message.listings.length > 0 && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {message.listings.map((listing) => (
                    <ListingCard
                      key={listing.listing_code}
                      listing={listing}
                      onOpen={(button) => onOpenListing(listing.listing_code, button)}
                    />
                  ))}
                </div>
              )}
              {message.visitProposal && (
                // The AI only proposed this slot; the person books it here.
                <BookVisitCard
                  listingCode={message.visitProposal.listing_code}
                  title={message.visitProposal.title}
                  proposedSlot={message.visitProposal.starts_at}
                />
              )}
            </div>
          ))}

          {sending && <ThinkingIndicator />}

          {error && !sending && (
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-3 text-sm text-red-200">
              <p className="flex-1">
                {error.status === 0
                  ? "Can't reach the Prop AI API. Is the backend running?"
                  : error.message}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={retry}
                disabled={voice.listening}
                className="gap-1.5"
              >
                <RotateCcw aria-hidden="true" />
                Retry
              </Button>
            </div>
          )}
        </div>

        <form
          className="flex items-center gap-2 border-t border-white/10 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            // While listening the voice is the input; Enter must not send a hidden draft.
            if (!voice.listening) submit(input);
          }}
        >
          <label htmlFor="chat-input" className="sr-only">
            Message Prop AI
          </label>
          <input
            id="chat-input"
            // While listening, show the words recognised so far.
            value={voice.listening ? voice.interim : input}
            readOnly={voice.listening}
            onChange={(e) => setInput(e.target.value)}
            maxLength={MAX_MESSAGE_LENGTH}
            placeholder={voice.listening ? "Listening…" : "e.g. 1BHK to rent in Powai under 50k"}
            autoComplete="off"
            className="h-11 flex-1 rounded-xl border border-white/15 bg-black/60 px-4 text-sm text-white outline-none placeholder:text-white/35 focus-visible:border-white/40 focus-visible:ring-2 focus-visible:ring-white/20"
          />
          <Button
            type="button"
            size="lg"
            variant="outline"
            onClick={toggleMic}
            // Stoppable even mid-request; otherwise blocked while a reply is pending.
            disabled={(sending && !voice.listening) || !voice.supported}
            title={voice.supported ? undefined : VOICE_UNSUPPORTED_HINT}
            aria-label={voice.listening ? "Stop listening" : "Start voice input"}
            aria-pressed={voice.listening}
            className={cn(
              "h-11 w-11 p-0",
              voice.listening && "border-red-400/60 bg-red-500/15 text-red-200"
            )}
          >
            {voice.listening ? <MicOff aria-hidden="true" /> : <Mic aria-hidden="true" />}
          </Button>
          <Button
            type="submit"
            size="lg"
            disabled={sending || voice.listening || !input.trim()}
            aria-label="Send message"
            className="h-11 w-11 p-0"
          >
            <SendHorizontal aria-hidden="true" />
          </Button>
        </form>
      </div>

      {voice.error && (
        <p className="mt-3 text-sm text-red-200" role="alert">
          {voice.error}
        </p>
      )}
      <p className="mt-3 text-xs text-white/40">
        {voice.supported
          ? "Voice is converted to text by your browser's speech service. "
          : `${VOICE_UNSUPPORTED_HINT} `}
        AI replies can be wrong. Listing cards come straight from the database (fictional demo
        data).
        {input.length > MAX_MESSAGE_LENGTH - 200 && (
          <span className="ml-2 text-white/60">
            {input.length}/{MAX_MESSAGE_LENGTH}
          </span>
        )}
      </p>
    </section>
  );
}

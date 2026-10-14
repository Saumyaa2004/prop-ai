import { useEffect, useRef, useState } from "react";
import { ApiError, sendChat } from "@/lib/api";
import { cleanReply, toApiHistory } from "@/lib/chat";
import type { ConversationMessage } from "@/lib/chat";

/** Max characters per message, same as the backend's ChatMessage. */
export const MAX_MESSAGE_LENGTH = 1000;

/**
 * Conversation state for the AI chat. Sending is a user action (a "mutation"),
 * unlike useApi, which re-loads data whenever its inputs change.
 */
export function useChat() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  // Cancel an in-flight request if the component unmounts.
  useEffect(() => () => controllerRef.current?.abort(), []);

  const ask = async (conversation: ConversationMessage[]) => {
    const controller = new AbortController();
    controllerRef.current = controller;
    setSending(true);
    setError(null);
    try {
      const response = await sendChat(toApiHistory(conversation), { signal: controller.signal });
      setMessages([
        ...conversation,
        { role: "assistant", content: cleanReply(response.reply), listings: response.listings },
      ]);
    } catch (caught) {
      if (controller.signal.aborted) return; // chat was reset or left; ignore
      setError(caught instanceof ApiError ? caught : new ApiError(0, "Unexpected error."));
    } finally {
      if (!controller.signal.aborted) setSending(false);
    }
  };

  /** Show the user's message immediately, then ask the agent. */
  const send = (text: string) => {
    const content = text.trim().slice(0, MAX_MESSAGE_LENGTH);
    if (!content || sending) return;
    const conversation: ConversationMessage[] = [...messages, { role: "user", content }];
    setMessages(conversation);
    void ask(conversation);
  };

  /** Re-send after an error, without duplicating the user's message. */
  const retry = () => {
    if (!sending && messages.at(-1)?.role === "user") void ask(messages);
  };

  const reset = () => {
    controllerRef.current?.abort();
    setMessages([]);
    setError(null);
    setSending(false);
  };

  return { messages, sending, error, send, retry, reset };
}

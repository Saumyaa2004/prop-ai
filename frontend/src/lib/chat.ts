import type { ChatMessage, Property } from "@/lib/api";

/** A message as the UI keeps it: assistant replies carry their listing cards. */
export interface ConversationMessage extends ChatMessage {
  listings?: Property[];
}

/** Same limit as the backend's ChatRequest (max 20 messages). */
export const MAX_HISTORY = 20;

/** What the API accepts: role + content only, newest MAX_HISTORY messages. */
export function toApiHistory(messages: ConversationMessage[]): ChatMessage[] {
  return messages.slice(-MAX_HISTORY).map(({ role, content }) => ({ role, content }));
}

/**
 * Defensive cleanup of the model's reply. The prompt asks for plain text, but
 * models don't always comply: drop markdown emphasis, normalise bullets.
 * (Rendered as text, never as HTML, so model output can't inject markup.)
 */
export function cleanReply(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/^\s*[*-]\s+/gm, "• ")
    .replace(/^#+\s*/gm, "")
    .trim();
}

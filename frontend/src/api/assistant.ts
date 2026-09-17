import { apiClient } from "./client";

export interface AssistantMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantChatResponse {
  reply: string;
  referenced_product_ids: string[];
}

export async function askAssistant(
  message: string,
  history: AssistantMessage[],
): Promise<AssistantChatResponse> {
  const { data } = await apiClient.post<AssistantChatResponse>("/assistant/chat", {
    message,
    history,
  });
  return data;
}

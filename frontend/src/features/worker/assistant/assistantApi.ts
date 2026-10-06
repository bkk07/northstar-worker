import { axiosClient } from "@/shared/api/axiosClient";

export type AssistantAction = {
  kind: string;
  label: string;
  task_id?: string | null;
  href?: string | null;
  approval_id?: string | null;
  decision?: string | null;
};

export type ChatReply = {
  reply: string;
  task_id?: string | null;
  actions: AssistantAction[];
};

// One call per chat turn (the backend routes intent and may launch a run).
export async function postChat(message: string): Promise<ChatReply> {
  const { data } = await axiosClient.post<ChatReply>("/api/chat", { message });
  return data;
}

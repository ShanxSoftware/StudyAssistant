// components/ChatWindow.tsx (standardized, extendable)
"use client";
import { useChat } from "@ai-sdk/react";

export default function ChatWindow({ agentId }: { agentId: string }) {
  const { messages, input, handleSubmit, isLoading } = useChat({
    api: "/api/chat",
    body: { agent_id: agentId },
  });
  // render markdown, tool calls, etc. — exact same as any modern chat UI
}
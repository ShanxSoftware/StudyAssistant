// app/api/chat/route.ts
import { xAI_Handler, MemoryStore } from "xaihandler"; // or relative
import { SupabaseMemoryStore } from "xaihandler/memorystore";

export async function POST(req: Request) {
  const { messages, user_id, agent_id } = await req.json();
  const memory = new MemoryStore({ backend: new SupabaseMemoryStore(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!) });
  const handler = new xAI_Handler({ memory_backend: memory.backend, user_id, agent_id });
  
  const context = isCollaborative 
  ? memory.get_collaborative_context(sessionId, agentId) 
  : memory.get_context(sessionId);
  // existing execution_loop + streaming logic here
  // return new StreamingTextResponse(stream);
}
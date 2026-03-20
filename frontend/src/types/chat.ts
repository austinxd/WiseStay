export interface Conversation { id: number; channel: string; status: string; created_at: string; last_message: string | null; messages?: Message[] }
export interface Message { id?: number; sender_type: 'guest' | 'ai' | 'system' | 'human'; content: string; created_at: string; tool_calls_summary?: { name: string; result: string }[] }

import api from '@/config/api';
import type { Conversation, Message } from '@/types/chat';

interface PaginatedResponse<T> { count: number; results: T[] }

export const chatService = {
  startConversation: (data: { reservation_id?: number; channel?: string }) =>
    api.post<{ conversation_id: number; status: string; is_new: boolean }>('/chatbot/conversations/start/', data).then(r => r.data),
  getConversations: () => api.get<PaginatedResponse<Conversation>>('/chatbot/conversations/').then(r => r.data),
  getConversation: (id: number) => api.get<Conversation>(`/chatbot/conversations/${id}/`).then(r => r.data),
  sendMessage: (conversationId: number, content: string) =>
    api.post<{ message_id: number; content: string; sender_type: string }>(`/chatbot/conversations/${conversationId}/messages/`, { content }).then(r => r.data),
  getMessages: (conversationId: number) => api.get<PaginatedResponse<Message>>(`/chatbot/conversations/${conversationId}/history/`).then(r => r.data),
};

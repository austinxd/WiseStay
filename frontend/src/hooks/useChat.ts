import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatService } from '@/services/chatService';
import { useAuthStore } from '@/stores/authStore';
import { WS_BASE_URL } from '@/config/constants';
import type { Message } from '@/types/chat';

export function useConversations() {
  return useQuery({ queryKey: ['conversations'], queryFn: chatService.getConversations });
}

export function useConversation(id: number) {
  return useQuery({ queryKey: ['conversation', id], queryFn: () => chatService.getConversation(id), enabled: !!id });
}

export function useSendMessage(conversationId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => chatService.sendMessage(conversationId, content),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conversation', conversationId] }),
  });
}

export function useChatWebSocket(conversationId: number) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const { accessToken } = useAuthStore();

  useEffect(() => {
    if (!conversationId || !accessToken) return;
    const ws = new WebSocket(`${WS_BASE_URL}/ws/chat/${conversationId}/?token=${accessToken}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'chunk') { setIsTyping(true); }
      else if (data.type === 'message_complete') {
        setIsTyping(false);
        setMessages(prev => [...prev, { sender_type: 'ai', content: data.content, created_at: new Date().toISOString() }]);
      } else if (data.type === 'error') { setIsTyping(false); }
    };
    ws.onclose = () => setIsTyping(false);
    wsRef.current = ws;
    return () => { ws.close(); };
  }, [conversationId, accessToken]);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content }));
      setMessages(prev => [...prev, { sender_type: 'guest', content, created_at: new Date().toISOString() }]);
    }
  }, []);

  return { messages, sendMessage, isTyping, setMessages };
}

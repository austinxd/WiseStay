import { useState, useEffect, useRef } from 'react';
import { useSendMessage, useConversation } from '@/hooks/useChat';
import { chatService } from '@/services/chatService';
import { Button } from '@/components/ui/Button';
import { PageSpinner } from '@/components/ui/Spinner';
import { Send, Bot, User } from 'lucide-react';

export function ChatPage() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { data: conversation } = useConversation(conversationId || 0);
  const sendMsg = useSendMessage(conversationId || 0);

  useEffect(() => {
    chatService.startConversation({ channel: 'web' }).then(r => setConversationId(r.conversation_id));
  }, []);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [conversation]);

  const handleSend = async () => {
    if (!input.trim() || !conversationId) return;
    const msg = input;
    setInput('');
    setLoading(true);
    try { await sendMsg.mutateAsync(msg); } catch {}
    setLoading(false);
  };

  const messages = conversation?.messages || [];

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <h1 className="text-2xl font-heading font-bold mb-4">AI Concierge</h1>
      <div className="flex-1 bg-white rounded-xl border overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && <p className="text-center text-gray-400 mt-8">Start a conversation with your WiseStay concierge</p>}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.sender_type === 'guest' ? 'justify-end' : ''}`}>
            {m.sender_type !== 'guest' && <div className="w-8 h-8 rounded-full bg-wisestay-100 flex items-center justify-center flex-shrink-0"><Bot className="w-4 h-4 text-wisestay-600" /></div>}
            <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 text-sm ${m.sender_type === 'guest' ? 'bg-wisestay-500 text-white' : 'bg-gray-100 text-gray-800'}`}>
              <p className="whitespace-pre-wrap">{m.content}</p>
            </div>
            {m.sender_type === 'guest' && <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0"><User className="w-4 h-4 text-gray-600" /></div>}
          </div>
        ))}
        {loading && <div className="flex gap-3"><div className="w-8 h-8 rounded-full bg-wisestay-100 flex items-center justify-center"><Bot className="w-4 h-4 text-wisestay-600" /></div><div className="bg-gray-100 rounded-2xl px-4 py-2.5 text-sm text-gray-400">Thinking...</div></div>}
        <div ref={messagesEndRef} />
      </div>
      <div className="flex gap-3 mt-4">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSend()} placeholder="Ask me anything..." className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-wisestay-300" />
        <Button onClick={handleSend} disabled={!input.trim() || loading}><Send className="w-5 h-5" /></Button>
      </div>
    </div>
  );
}

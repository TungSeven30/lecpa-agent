'use client';

import { useEffect, useRef, useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { ChatMessage } from './chat-message';
import { ChatInput } from './chat-input';
import { useChatStore } from '@/lib/store';
import { streamChat, type Citation } from '@/lib/api';

interface ChatContainerProps {
  caseId?: string;
  onCitationClick?: (citation: Citation) => void;
}

export function ChatContainer({ caseId, onCitationClick }: ChatContainerProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    messages,
    isLoading,
    addMessage,
    updateLastMessage,
    setLoading,
    setCaseId,
    clearMessages,
  } = useChatStore();

  // Set case context
  useEffect(() => {
    setCaseId(caseId || null);
  }, [caseId, setCaseId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (content: string) => {
    // Add user message
    addMessage({
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    });

    // Add empty assistant message
    addMessage({
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    });

    setLoading(true);

    try {
      const body: Record<string, unknown> = {
        message: content,
        history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      };

      if (caseId) {
        body.case_id = caseId;
      }

      for await (const chunk of streamChat('/chat', body)) {
        updateLastMessage(chunk);
      }
    } catch (error) {
      console.error('Chat error:', error);
      updateLastMessage(
        '\n\n*An error occurred while processing your request. Please try again.*'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center px-4">
            <div className="rounded-full bg-primary-100 p-4 dark:bg-primary-900">
              <MessageSquare className="h-8 w-8 text-primary-600 dark:text-primary-400" aria-hidden="true" />
            </div>
            <h3 className="mt-4 text-lg font-medium text-foreground">
              Start a conversation
            </h3>
            <p className="mt-2 max-w-sm text-sm text-muted-foreground">
              Ask questions about your clients, documents, or tax matters. I can
              help you find information and draft responses.
            </p>
            <div className="mt-6 space-y-2 text-sm">
              <p className="font-medium text-foreground">Try asking:</p>
              <ul className="space-y-1 text-muted-foreground">
                <li>&quot;Summarize the W-2s for client ABC&quot;</li>
                <li>&quot;What documents are missing for the 2024 return?&quot;</li>
                <li>&quot;Draft a response to the CP2000 notice&quot;</li>
              </ul>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {messages.map((message, index) => (
              <ChatMessage
                key={index}
                message={message}
                onCitationClick={onCitationClick}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}

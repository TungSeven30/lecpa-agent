'use client';

import { User, Bot, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType, Citation } from '@/lib/api';

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick?: (citation: Citation) => void;
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-4 p-4',
        isUser ? 'bg-white' : 'bg-gray-50'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary-600' : 'bg-gray-600'
        )}
      >
        {isUser ? (
          <User className="h-5 w-5 text-white" />
        ) : (
          <Bot className="h-5 w-5 text-white" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <p className="mb-1 text-sm font-medium text-gray-900">
          {isUser ? 'You' : 'Assistant'}
        </p>
        <div className="prose prose-sm max-w-none text-gray-700">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium text-gray-500">Sources:</p>
            <div className="flex flex-wrap gap-2">
              {message.citations.map((citation, index) => (
                <button
                  key={citation.chunk_id}
                  onClick={() => onCitationClick?.(citation)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-primary-50 px-2.5 py-1.5 text-xs font-medium text-primary-700 hover:bg-primary-100"
                >
                  <FileText className="h-3 w-3" />
                  <span className="max-w-[200px] truncate">
                    {citation.document_filename}
                  </span>
                  {citation.page_start && (
                    <span className="text-primary-500">
                      p.{citation.page_start}
                      {citation.page_end && citation.page_end !== citation.page_start
                        ? `-${citation.page_end}`
                        : ''}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

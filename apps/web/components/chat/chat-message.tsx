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
                isUser ? 'bg-card' : 'bg-muted/50'
            )}
        >
            {/* Avatar */}
            <div
                className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                    isUser ? 'bg-primary-600 dark:bg-primary-500' : 'bg-muted-foreground'
                )}
            >
                {isUser ? (
                    <User className="h-5 w-5 text-white" aria-hidden="true" />
                ) : (
                    <Bot className="h-5 w-5 text-white" aria-hidden="true" />
                )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
                <p className="mb-1 text-sm font-medium text-foreground">
                    {isUser ? 'You' : 'Assistant'}
                </p>
                <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>

                {/* Citations */}
                {message.citations && message.citations.length > 0 && (
                    <div className="mt-4">
                        <p className="mb-2 text-xs font-medium text-muted-foreground">Sources:</p>
                        <div className="flex flex-wrap gap-2">
                            {message.citations.map((citation) => (
                                <button
                                    key={citation.chunk_id}
                                    onClick={() => onCitationClick?.(citation)}
                                    className="inline-flex min-h-[36px] items-center gap-1.5 rounded-md bg-primary-100 px-2.5 py-1.5 text-xs font-medium text-primary-700 transition-colors hover:bg-primary-200 dark:bg-primary-900 dark:text-primary-300 dark:hover:bg-primary-800"
                                >
                                    <FileText className="h-3 w-3" aria-hidden="true" />
                                    <span className="max-w-[200px] truncate">
                                        {citation.document_filename}
                                    </span>
                                    {citation.page_start && (
                                        <span className="text-primary-600 dark:text-primary-400">
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

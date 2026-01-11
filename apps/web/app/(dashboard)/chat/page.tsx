'use client';

import { useState } from 'react';
import { X, FileText } from 'lucide-react';
import { ChatContainer } from '@/components/chat';
import { Card, Button } from '@/components/ui';
import type { Citation } from '@/lib/api';

export default function ChatPage() {
    const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

    return (
        <div className="flex h-full">
            {/* Chat area */}
            <div className="flex flex-1 flex-col">
                <div className="border-b border-border bg-card px-6 py-4">
                    <h1 className="text-xl font-semibold text-foreground">Chat</h1>
                    <p className="text-sm text-muted-foreground">
                        Ask questions about clients and documents
                    </p>
                </div>
                <div className="flex-1">
                    <ChatContainer onCitationClick={setSelectedCitation} />
                </div>
            </div>

            {/* Citation panel */}
            {selectedCitation && (
                <div className="w-96 border-l border-border bg-card">
                    <div className="flex items-center justify-between border-b border-border px-4 py-3">
                        <h3 className="font-medium text-foreground">Source Document</h3>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedCitation(null)}
                            className="min-h-[44px] min-w-[44px]"
                            aria-label="Close citation panel"
                        >
                            <X className="h-5 w-5" aria-hidden="true" />
                        </Button>
                    </div>
                    <div className="p-4">
                        <Card>
                            <div className="p-4">
                                <div className="flex items-center gap-3">
                                    <div className="rounded-lg bg-primary-100 p-2 dark:bg-primary-900">
                                        <FileText className="h-5 w-5 text-primary-600 dark:text-primary-400" aria-hidden="true" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-foreground">
                                            {selectedCitation.document_filename}
                                        </p>
                                        {selectedCitation.page_start && (
                                            <p className="text-sm text-muted-foreground">
                                                Page {selectedCitation.page_start}
                                                {selectedCitation.page_end &&
                                                selectedCitation.page_end !== selectedCitation.page_start
                                                    ? ` - ${selectedCitation.page_end}`
                                                    : ''}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </Card>

                        <div className="mt-4">
                            <p className="mb-2 text-sm font-medium text-foreground">
                                Relevant Excerpt:
                            </p>
                            <div className="rounded-lg bg-muted p-3 text-sm text-foreground">
                                {selectedCitation.snippet}
                            </div>
                        </div>

                        <div className="mt-4">
                            <p className="text-xs text-muted-foreground">
                                Relevance Score:{' '}
                                <span className="font-medium tabular-nums">
                                    {(selectedCitation.relevance_score * 100).toFixed(1)}%
                                </span>
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

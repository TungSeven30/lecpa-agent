'use client';

import { useState } from 'react';
import { X, FileText } from 'lucide-react';
import { ChatContainer } from '@/components/chat';
import { Card } from '@/components/ui';
import type { Citation } from '@/lib/api';

export default function ChatPage() {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  return (
    <div className="flex h-full">
      {/* Chat area */}
      <div className="flex flex-1 flex-col">
        <div className="border-b bg-white px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">Chat</h1>
          <p className="text-sm text-gray-600">
            Ask questions about clients and documents
          </p>
        </div>
        <div className="flex-1">
          <ChatContainer onCitationClick={setSelectedCitation} />
        </div>
      </div>

      {/* Citation panel */}
      {selectedCitation && (
        <div className="w-96 border-l bg-white">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h3 className="font-medium text-gray-900">Source Document</h3>
            <button
              onClick={() => setSelectedCitation(null)}
              className="rounded p-1 hover:bg-gray-100"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
          <div className="p-4">
            <Card>
              <div className="p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary-100 p-2">
                    <FileText className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      {selectedCitation.document_filename}
                    </p>
                    {selectedCitation.page_start && (
                      <p className="text-sm text-gray-500">
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
              <p className="mb-2 text-sm font-medium text-gray-700">
                Relevant Excerpt:
              </p>
              <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
                {selectedCitation.snippet}
              </div>
            </div>

            <div className="mt-4">
              <p className="text-xs text-gray-500">
                Relevance Score:{' '}
                {(selectedCitation.relevance_score * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

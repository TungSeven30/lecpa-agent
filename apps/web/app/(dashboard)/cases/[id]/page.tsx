'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  FileText,
  MessageSquare,
  FileEdit,
  Settings,
} from 'lucide-react';
import Link from 'next/link';
import { Button, Card, Badge } from '@/components/ui';
import { DocumentList, ArtifactList } from '@/components/cases';
import { ChatContainer } from '@/components/chat';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

type Tab = 'documents' | 'chat' | 'artifacts';

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
  open: 'default',
  in_progress: 'default',
  pending_review: 'warning',
  needs_info: 'error',
  completed: 'success',
  closed: 'secondary',
};

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = params.id as string;
  const [activeTab, setActiveTab] = useState<Tab>('documents');

  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => api.getCase(caseId),
    enabled: !!caseId,
  });

  const tabs = [
    { id: 'documents' as Tab, label: 'Documents', icon: FileText },
    { id: 'chat' as Tab, label: 'Chat', icon: MessageSquare },
    { id: 'artifacts' as Tab, label: 'Artifacts', icon: FileEdit },
  ];

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-gray-500">Loading case...</div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500">Case not found</p>
          <Link href="/cases">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Cases
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/cases">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-semibold text-gray-900">
                  {caseData.client?.name || 'Unknown Client'}
                </h1>
                <Badge variant={statusColors[caseData.status] || 'default'}>
                  {caseData.status.replace('_', ' ')}
                </Badge>
              </div>
              <p className="text-sm text-gray-600">
                {caseData.client?.client_code} &bull; {caseData.case_type} &bull;{' '}
                {caseData.year}
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Button>
        </div>

        {/* Tabs */}
        <div className="mt-4 flex gap-4 border-b -mb-px">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 border-b-2 px-1 pb-3 text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'documents' && (
          <div className="h-full overflow-y-auto p-6">
            <DocumentList caseId={caseId} />
          </div>
        )}

        {activeTab === 'chat' && (
          <ChatContainer caseId={caseId} />
        )}

        {activeTab === 'artifacts' && (
          <div className="h-full overflow-y-auto p-6">
            <ArtifactList caseId={caseId} />
          </div>
        )}
      </div>
    </div>
  );
}

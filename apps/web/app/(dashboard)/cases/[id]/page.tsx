'use client';

import { useState, useCallback, useId } from 'react';
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
import { Button, Badge } from '@/components/ui';
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
    closed: 'default',
};

const tabs: Array<{ id: Tab; label: string; icon: typeof FileText }> = [
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'artifacts', label: 'Artifacts', icon: FileEdit },
];

export default function CaseDetailPage() {
    const params = useParams();
    const caseId = params.id as string;
    const [activeTab, setActiveTab] = useState<Tab>('documents');
    const tabIdPrefix = useId();

    const { data: caseData, isLoading } = useQuery({
        queryKey: ['case', caseId],
        queryFn: () => api.getCase(caseId),
        enabled: !!caseId,
    });

    // Handle keyboard navigation for tabs
    const handleTabKeyDown = useCallback(
        (e: React.KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
            let newIndex: number | null = null;

            if (e.key === 'ArrowLeft') {
                newIndex = currentIndex === 0 ? tabs.length - 1 : currentIndex - 1;
            } else if (e.key === 'ArrowRight') {
                newIndex = currentIndex === tabs.length - 1 ? 0 : currentIndex + 1;
            } else if (e.key === 'Home') {
                newIndex = 0;
            } else if (e.key === 'End') {
                newIndex = tabs.length - 1;
            }

            if (newIndex !== null) {
                e.preventDefault();
                setActiveTab(tabs[newIndex].id);
                // Focus the new tab
                const newTabElement = document.getElementById(
                    `${tabIdPrefix}-tab-${tabs[newIndex].id}`
                );
                newTabElement?.focus();
            }
        },
        [tabIdPrefix]
    );

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
                            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
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
                        <Link href="/cases" aria-label="Back to cases">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="min-h-[44px] min-w-[44px]"
                            >
                                <ArrowLeft className="h-5 w-5" aria-hidden="true" />
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
                                {caseData.client?.client_code} &bull; {caseData.case_type}{' '}
                                &bull; {caseData.year}
                            </p>
                        </div>
                    </div>
                    <Button variant="outline" size="sm" className="min-h-[44px]">
                        <Settings className="mr-2 h-4 w-4" aria-hidden="true" />
                        Settings
                    </Button>
                </div>

                {/* Tabs - Accessible */}
                <div
                    role="tablist"
                    aria-label="Case sections"
                    className="-mb-px mt-4 flex gap-1 border-b"
                >
                    {tabs.map((tab, index) => {
                        const isActive = activeTab === tab.id;
                        const TabIcon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                id={`${tabIdPrefix}-tab-${tab.id}`}
                                role="tab"
                                aria-selected={isActive}
                                aria-controls={`${tabIdPrefix}-panel-${tab.id}`}
                                tabIndex={isActive ? 0 : -1}
                                onClick={() => setActiveTab(tab.id)}
                                onKeyDown={(e) => handleTabKeyDown(e, index)}
                                className={cn(
                                    'flex min-h-[44px] items-center gap-2 border-b-2 px-4 text-sm font-medium transition-colors',
                                    isActive
                                        ? 'border-primary-600 text-primary-600'
                                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                )}
                            >
                                <TabIcon className="h-4 w-4" aria-hidden="true" />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Tab Panels - Accessible */}
            <div className="flex-1 overflow-hidden">
                <div
                    id={`${tabIdPrefix}-panel-documents`}
                    role="tabpanel"
                    aria-labelledby={`${tabIdPrefix}-tab-documents`}
                    hidden={activeTab !== 'documents'}
                    tabIndex={0}
                    className="h-full overflow-y-auto p-6"
                >
                    {activeTab === 'documents' && <DocumentList caseId={caseId} />}
                </div>

                <div
                    id={`${tabIdPrefix}-panel-chat`}
                    role="tabpanel"
                    aria-labelledby={`${tabIdPrefix}-tab-chat`}
                    hidden={activeTab !== 'chat'}
                    tabIndex={0}
                    className="h-full"
                >
                    {activeTab === 'chat' && <ChatContainer caseId={caseId} />}
                </div>

                <div
                    id={`${tabIdPrefix}-panel-artifacts`}
                    role="tabpanel"
                    aria-labelledby={`${tabIdPrefix}-tab-artifacts`}
                    hidden={activeTab !== 'artifacts'}
                    tabIndex={0}
                    className="h-full overflow-y-auto p-6"
                >
                    {activeTab === 'artifacts' && <ArtifactList caseId={caseId} />}
                </div>
            </div>
        </div>
    );
}

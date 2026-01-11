'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    FileEdit,
    Mail,
    CheckSquare,
    FileWarning,
    Copy,
    FileSpreadsheet,
    ClipboardCheck,
} from 'lucide-react';
import { Button, Card, Badge, Skeleton } from '@/components/ui';
import { useToast } from '@/components/ui/toast';
import { api, type Artifact } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { ArtifactViewer } from '@/components/artifacts/artifact-viewer';

function ArtifactSkeleton() {
    return (
        <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <div className="flex items-center gap-2">
                        <Skeleton className="h-5 w-24 rounded-full" />
                        <Skeleton className="h-3 w-16" />
                    </div>
                </div>
            </div>
            <Skeleton className="h-8 w-8 rounded-md" />
        </div>
    );
}

interface ArtifactListProps {
    caseId: string;
    onViewArtifact?: (artifact: Artifact) => void;
}

const artifactIcons: Record<string, React.ReactNode> = {
    missing_docs_email: (
        <Mail className="h-5 w-5 text-blue-600" aria-hidden="true" />
    ),
    organizer_checklist: (
        <CheckSquare className="h-5 w-5 text-green-600" aria-hidden="true" />
    ),
    notice_response: (
        <FileWarning className="h-5 w-5 text-orange-600" aria-hidden="true" />
    ),
    qc_memo: (
        <ClipboardCheck className="h-5 w-5 text-purple-600" aria-hidden="true" />
    ),
    extraction_result: (
        <FileSpreadsheet className="h-5 w-5 text-indigo-600" aria-hidden="true" />
    ),
    summary: <FileEdit className="h-5 w-5 text-gray-600" aria-hidden="true" />,
    custom: <FileEdit className="h-5 w-5 text-gray-600" aria-hidden="true" />,
};

const artifactLabels: Record<string, string> = {
    missing_docs_email: 'Missing Docs Email',
    organizer_checklist: 'Organizer Checklist',
    notice_response: 'Notice Response',
    qc_memo: 'QC Memo',
    extraction_result: 'Extraction Result',
    summary: 'Summary',
    custom: 'Custom',
};

/**
 * Artifact list component for displaying and managing case artifacts.
 *
 * Displays generated documents with copy and view functionality.
 *
 * Args:
 *     caseId: The ID of the case to display artifacts for
 *     onViewArtifact: Callback when an artifact is selected for viewing
 */
export function ArtifactList({ caseId, onViewArtifact }: ArtifactListProps) {
    const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(
        null
    );
    const { showToast } = useToast();

    const { data: artifacts, isLoading } = useQuery({
        queryKey: ['artifacts', caseId],
        queryFn: () => api.getCaseArtifacts(caseId),
    });

    const handleCopy = async (content: string, title: string): Promise<void> => {
        try {
            await navigator.clipboard.writeText(content);
            showToast(`"${title}" copied to clipboard`, 'success');
        } catch (error) {
            const message =
                error instanceof Error ? error.message : 'Failed to copy';
            showToast(message, 'error');
        }
    };

    const handleViewArtifact = (artifact: Artifact): void => {
        setSelectedArtifact(artifact);
        onViewArtifact?.(artifact);
    };

    return (
        <div>
            <div className="mb-4">
                <h3 className="text-lg font-medium text-foreground">Artifacts</h3>
                <p className="text-sm text-muted-foreground">
                    Generated documents and drafts
                </p>
            </div>

            {isLoading ? (
                <div className="space-y-2">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <ArtifactSkeleton key={i} />
                    ))}
                </div>
            ) : artifacts && artifacts.length > 0 ? (
                <div className="space-y-2">
                    {artifacts.map((artifact) => (
                        <Card
                            key={artifact.id}
                            className="cursor-pointer transition-all duration-200 hover:bg-accent hover:shadow-sm"
                            onClick={() => handleViewArtifact(artifact)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    handleViewArtifact(artifact);
                                }
                            }}
                        >
                            <div className="flex items-center justify-between p-4">
                                <div className="flex min-w-0 items-center gap-3">
                                    <div className="flex-shrink-0 rounded-lg bg-muted p-2">
                                        {artifactIcons[artifact.artifact_type] || (
                                            <FileEdit
                                                className="h-5 w-5 text-muted-foreground"
                                                aria-hidden="true"
                                            />
                                        )}
                                    </div>
                                    <div className="min-w-0">
                                        <p
                                            className="max-w-[250px] truncate font-medium text-foreground"
                                            title={artifact.title}
                                        >
                                            {artifact.title}
                                        </p>
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <Badge variant="secondary">
                                                {artifactLabels[artifact.artifact_type] ||
                                                    artifact.artifact_type}
                                            </Badge>
                                            <span>v{artifact.version}</span>
                                            <span>&bull;</span>
                                            <span>{formatDate(artifact.updated_at)}</span>
                                        </div>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        handleCopy(artifact.content, artifact.title);
                                    }}
                                    aria-label={`Copy ${artifact.title} to clipboard`}
                                >
                                    <Copy className="h-4 w-4" aria-hidden="true" />
                                </Button>
                            </div>
                        </Card>
                    ))}
                </div>
            ) : (
                <Card>
                    <div className="py-12 text-center">
                        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                            <FileEdit
                                className="h-8 w-8 text-muted-foreground"
                                aria-hidden="true"
                            />
                        </div>
                        <h3 className="mt-4 text-lg font-medium text-foreground">
                            No artifacts yet
                        </h3>
                        <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
                            Use the chat to generate emails, checklists, and more
                        </p>
                    </div>
                </Card>
            )}

            {/* Artifact Viewer Modal */}
            <ArtifactViewer
                artifact={selectedArtifact}
                onClose={() => setSelectedArtifact(null)}
            />
        </div>
    );
}

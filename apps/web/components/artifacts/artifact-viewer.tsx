'use client';

import { useState, useEffect, useId } from 'react';
import { X, Download, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Button, Badge } from '@/components/ui';
import { useFocusTrap } from '@/lib/hooks/use-focus-trap';
import type { Artifact } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface ArtifactViewerProps {
    artifact: Artifact | null;
    onClose: () => void;
}

/**
 * Modal component for viewing artifact content.
 *
 * Displays artifact details with copy and download functionality.
 * Implements accessible modal pattern with focus trap and keyboard support.
 *
 * Args:
 *     artifact: The artifact to display, or null if modal should be hidden
 *     onClose: Callback when modal should close
 */
export function ArtifactViewer({ artifact, onClose }: ArtifactViewerProps) {
    const [copied, setCopied] = useState(false);
    const titleId = useId();
    const isOpen = artifact !== null;
    const focusTrapRef = useFocusTrap(isOpen);

    // Handle Escape key to close modal
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (e: KeyboardEvent): void => {
            if (e.key === 'Escape') {
                onClose();
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);

    // Prevent body scroll when modal is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [isOpen]);

    if (!artifact) return null;

    const handleCopy = async (): Promise<void> => {
        try {
            await navigator.clipboard.writeText(artifact.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy:', error);
        }
    };

    const handleDownload = (): void => {
        const blob = new Blob([artifact.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${artifact.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleBackdropClick = (e: React.MouseEvent): void => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const renderContent = (): React.ReactNode => {
        // Render content as markdown by default
        return (
            <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-p:text-gray-700 prose-a:text-primary-600 prose-strong:text-gray-900">
                <ReactMarkdown>{artifact.content}</ReactMarkdown>
            </div>
        );
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={handleBackdropClick}
            aria-hidden="true"
        >
            <div
                ref={focusTrapRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-lg bg-white shadow-xl"
            >
                {/* Header */}
                <div className="flex items-start justify-between border-b p-6">
                    <div className="min-w-0 flex-1">
                        <h2
                            id={titleId}
                            className="truncate text-xl font-semibold text-gray-900"
                        >
                            {artifact.title}
                        </h2>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                            <Badge variant="secondary">
                                {artifact.artifact_type.replace(/_/g, ' ')}
                            </Badge>
                            <span className="text-sm text-gray-500">
                                v{artifact.version} &bull; {formatDate(artifact.updated_at)}
                            </span>
                        </div>
                    </div>

                    {/* Action buttons */}
                    <div className="ml-4 flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleCopy}
                            className="flex min-h-[44px] items-center gap-2"
                            aria-label={copied ? 'Copied to clipboard' : 'Copy to clipboard'}
                        >
                            {copied ? (
                                <>
                                    <Check className="h-4 w-4" aria-hidden="true" />
                                    Copied
                                </>
                            ) : (
                                <>
                                    <Copy className="h-4 w-4" aria-hidden="true" />
                                    Copy
                                </>
                            )}
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleDownload}
                            className="flex min-h-[44px] items-center gap-2"
                            aria-label="Download artifact"
                        >
                            <Download className="h-4 w-4" aria-hidden="true" />
                            Download
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onClose}
                            className="ml-2 min-h-[44px] min-w-[44px]"
                            aria-label="Close dialog"
                        >
                            <X className="h-5 w-5" aria-hidden="true" />
                        </Button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">{renderContent()}</div>

                {/* Footer */}
                <div className="border-t bg-gray-50 p-4">
                    <p className="text-center text-xs text-gray-500">
                        Generated by Le CPA Agent
                    </p>
                </div>
            </div>
        </div>
    );
}

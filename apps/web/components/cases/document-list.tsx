'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    FileText,
    Upload,
    CheckCircle,
    Clock,
    AlertCircle,
    Eye,
} from 'lucide-react';
import { Button, Card, Badge } from '@/components/ui';
import { useToast } from '@/components/ui/toast';
import { api, type Document } from '@/lib/api';
import { cn } from '@/lib/utils';

interface DocumentListProps {
    caseId: string;
    onViewDocument?: (document: Document) => void;
}

const statusIcons: Record<string, React.ReactNode> = {
    ready: <CheckCircle className="h-4 w-4 text-green-500" aria-hidden="true" />,
    pending: <Clock className="h-4 w-4 text-yellow-500" aria-hidden="true" />,
    extracting: (
        <Clock className="h-4 w-4 text-blue-500 animate-spin" aria-hidden="true" />
    ),
    embedding: (
        <Clock className="h-4 w-4 text-blue-500 animate-spin" aria-hidden="true" />
    ),
    failed: <AlertCircle className="h-4 w-4 text-red-500" aria-hidden="true" />,
};

const statusLabels: Record<string, string> = {
    ready: 'Ready',
    pending: 'Pending',
    extracting: 'Processing',
    canonicalizing: 'Processing',
    chunking: 'Processing',
    embedding: 'Indexing',
    failed: 'Failed',
};

/**
 * Document list component for displaying and managing case documents.
 *
 * Supports file upload, status tracking, and document viewing.
 *
 * Args:
 *     caseId: The ID of the case to display documents for
 *     onViewDocument: Callback when a document is selected for viewing
 */
export function DocumentList({ caseId, onViewDocument }: DocumentListProps) {
    const [isUploading, setIsUploading] = useState(false);
    const { showToast } = useToast();

    const {
        data: documents,
        isLoading,
        refetch,
    } = useQuery({
        queryKey: ['documents', caseId],
        queryFn: () => api.getCaseDocuments(caseId),
    });

    const handleUpload = async (
        e: React.ChangeEvent<HTMLInputElement>
    ): Promise<void> => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        setIsUploading(true);
        try {
            for (const file of Array.from(files)) {
                await api.uploadDocument(caseId, file);
            }
            showToast(
                `${files.length} document${files.length > 1 ? 's' : ''} uploaded successfully`,
                'success'
            );
            refetch();
        } catch (error) {
            const message =
                error instanceof Error ? error.message : 'Upload failed';
            showToast(message, 'error');
        } finally {
            setIsUploading(false);
            e.target.value = '';
        }
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <div>
            <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">Documents</h3>
                <label className="cursor-pointer">
                    <input
                        type="file"
                        multiple
                        accept=".pdf,.docx,.xlsx,.xls,.doc"
                        onChange={handleUpload}
                        className="sr-only"
                        disabled={isUploading}
                        aria-label="Upload documents"
                    />
                    <span
                        className={cn(
                            'inline-flex min-h-[44px] items-center justify-center rounded-md bg-primary-600 px-4 text-sm font-medium text-white transition-colors hover:bg-primary-700',
                            isUploading && 'opacity-50 cursor-not-allowed'
                        )}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                                e.currentTarget.click();
                            }
                        }}
                    >
                        {isUploading ? (
                            <>
                                <svg
                                    className="mr-2 h-4 w-4 animate-spin"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    aria-hidden="true"
                                >
                                    <circle
                                        className="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        strokeWidth="4"
                                    />
                                    <path
                                        className="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                    />
                                </svg>
                                Uploading...
                            </>
                        ) : (
                            <>
                                <Upload className="mr-2 h-4 w-4" aria-hidden="true" />
                                Upload
                            </>
                        )}
                    </span>
                </label>
            </div>

            {isLoading ? (
                <div className="py-8 text-center text-gray-500">
                    Loading documents...
                </div>
            ) : documents && documents.length > 0 ? (
                <div className="space-y-2">
                    {documents.map((doc) => (
                        <Card
                            key={doc.id}
                            className={cn(
                                'cursor-pointer transition-colors hover:bg-gray-50',
                                doc.processing_status === 'failed' &&
                                    'border-red-200 bg-red-50'
                            )}
                            onClick={() => onViewDocument?.(doc)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    onViewDocument?.(doc);
                                }
                            }}
                        >
                            <div className="flex items-center justify-between p-4">
                                <div className="flex min-w-0 items-center gap-3">
                                    <div className="flex-shrink-0 rounded-lg bg-gray-100 p-2">
                                        <FileText
                                            className="h-5 w-5 text-gray-600"
                                            aria-hidden="true"
                                        />
                                    </div>
                                    <div className="min-w-0">
                                        <p
                                            className="max-w-[200px] truncate font-medium text-gray-900"
                                            title={doc.filename}
                                        >
                                            {doc.filename}
                                        </p>
                                        <div className="flex items-center gap-2 text-sm text-gray-500">
                                            <span>{formatFileSize(doc.file_size)}</span>
                                            {doc.page_count && (
                                                <span>&bull; {doc.page_count} pages</span>
                                            )}
                                            {doc.is_ocr && (
                                                <Badge variant="secondary" className="text-xs">
                                                    OCR
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex flex-shrink-0 items-center gap-3">
                                    {doc.tags && doc.tags.length > 0 && (
                                        <div className="flex gap-1">
                                            {doc.tags.slice(0, 2).map((tag) => (
                                                <Badge
                                                    key={tag}
                                                    variant="default"
                                                    className="text-xs"
                                                >
                                                    {tag}
                                                </Badge>
                                            ))}
                                        </div>
                                    )}
                                    <div className="flex items-center gap-1.5">
                                        {statusIcons[doc.processing_status] ||
                                            statusIcons.pending}
                                        <span className="text-sm text-gray-600">
                                            {statusLabels[doc.processing_status] ||
                                                doc.processing_status}
                                        </span>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="ml-2"
                                        aria-label={`View ${doc.filename}`}
                                    >
                                        <Eye className="h-4 w-4" aria-hidden="true" />
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            ) : (
                <Card>
                    <div className="py-8 text-center">
                        <FileText
                            className="mx-auto h-10 w-10 text-gray-400"
                            aria-hidden="true"
                        />
                        <p className="mt-2 text-sm text-gray-500">
                            No documents uploaded yet
                        </p>
                        <label className="mt-4 inline-block cursor-pointer">
                            <input
                                type="file"
                                multiple
                                accept=".pdf,.docx,.xlsx,.xls,.doc"
                                onChange={handleUpload}
                                className="sr-only"
                                aria-label="Upload documents"
                            />
                            <span
                                className="inline-flex min-h-[44px] items-center justify-center rounded-md border border-gray-300 bg-white px-4 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-100"
                                role="button"
                                tabIndex={0}
                            >
                                <Upload className="mr-2 h-4 w-4" aria-hidden="true" />
                                Upload Documents
                            </span>
                        </label>
                    </div>
                </Card>
            )}
        </div>
    );
}

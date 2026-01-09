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
import { api, type Document } from '@/lib/api';
import { formatDate, cn } from '@/lib/utils';

interface DocumentListProps {
  caseId: string;
  onViewDocument?: (document: Document) => void;
}

const statusIcons: Record<string, React.ReactNode> = {
  ready: <CheckCircle className="h-4 w-4 text-green-500" />,
  pending: <Clock className="h-4 w-4 text-yellow-500" />,
  extracting: <Clock className="h-4 w-4 text-blue-500 animate-pulse" />,
  embedding: <Clock className="h-4 w-4 text-blue-500 animate-pulse" />,
  failed: <AlertCircle className="h-4 w-4 text-red-500" />,
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

export function DocumentList({ caseId, onViewDocument }: DocumentListProps) {
  const [isUploading, setIsUploading] = useState(false);

  const { data: documents, isLoading, refetch } = useQuery({
    queryKey: ['documents', caseId],
    queryFn: () => api.getCaseDocuments(caseId),
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      for (const file of Array.from(files)) {
        await api.uploadDocument(caseId, file);
      }
      refetch();
    } catch (error) {
      console.error('Upload failed:', error);
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
        <label>
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.xlsx,.xls,.doc"
            onChange={handleUpload}
            className="hidden"
            disabled={isUploading}
          />
          <Button
            as="span"
            isLoading={isUploading}
            className="cursor-pointer"
          >
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </Button>
        </label>
      </div>

      {isLoading ? (
        <div className="py-8 text-center text-gray-500">Loading documents...</div>
      ) : documents && documents.length > 0 ? (
        <div className="space-y-2">
          {documents.map((doc) => (
            <Card
              key={doc.id}
              className={cn(
                'cursor-pointer transition-colors hover:bg-gray-50',
                doc.processing_status === 'failed' && 'border-red-200 bg-red-50'
              )}
              onClick={() => onViewDocument?.(doc)}
            >
              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-gray-100 p-2">
                    <FileText className="h-5 w-5 text-gray-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{doc.filename}</p>
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <span>{formatFileSize(doc.file_size)}</span>
                      {doc.page_count && <span>&bull; {doc.page_count} pages</span>}
                      {doc.is_ocr && (
                        <Badge variant="secondary" className="text-xs">
                          OCR
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {doc.tags && doc.tags.length > 0 && (
                    <div className="flex gap-1">
                      {doc.tags.slice(0, 2).map((tag) => (
                        <Badge key={tag} variant="default" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-1.5">
                    {statusIcons[doc.processing_status] || statusIcons.pending}
                    <span className="text-sm text-gray-600">
                      {statusLabels[doc.processing_status] || doc.processing_status}
                    </span>
                  </div>
                  <Button variant="ghost" size="sm" className="ml-2">
                    <Eye className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <div className="py-8 text-center">
            <FileText className="mx-auto h-10 w-10 text-gray-400" />
            <p className="mt-2 text-sm text-gray-500">
              No documents uploaded yet
            </p>
            <label className="mt-4 inline-block">
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.xlsx,.xls,.doc"
                onChange={handleUpload}
                className="hidden"
              />
              <Button as="span" variant="outline" className="cursor-pointer">
                <Upload className="mr-2 h-4 w-4" />
                Upload Documents
              </Button>
            </label>
          </div>
        </Card>
      )}
    </div>
  );
}

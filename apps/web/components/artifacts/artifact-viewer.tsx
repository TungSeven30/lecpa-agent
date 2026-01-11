'use client';

import { useState } from 'react';
import { X, Download, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Button, Badge } from '@/components/ui';
import type { Artifact } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onClose: () => void;
}

export function ArtifactViewer({ artifact, onClose }: ArtifactViewerProps) {
  const [copied, setCopied] = useState(false);

  if (!artifact) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const handleDownload = () => {
    const extension = artifact.content_format === 'json' ? 'json' : 'md';
    const blob = new Blob([artifact.content], {
      type: artifact.content_format === 'json' ? 'application/json' : 'text/markdown'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const renderContent = () => {
    if (artifact.content_format === 'markdown') {
      return (
        <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-p:text-gray-700 prose-a:text-blue-600 prose-strong:text-gray-900">
          <ReactMarkdown>{artifact.content}</ReactMarkdown>
        </div>
      );
    } else if (artifact.content_format === 'json') {
      try {
        const parsed = JSON.parse(artifact.content);
        return (
          <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        );
      } catch {
        return <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">{artifact.content}</pre>;
      }
    } else if (artifact.content_format === 'html') {
      return (
        <div
          className="prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: artifact.content }}
        />
      );
    } else {
      return <pre className="whitespace-pre-wrap text-sm text-gray-700">{artifact.content}</pre>;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-semibold text-gray-900 truncate">
              {artifact.title}
            </h2>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <Badge variant="secondary">{artifact.artifact_type.replace(/_/g, ' ')}</Badge>
              <Badge variant={artifact.is_draft ? 'outline' : 'default'}>
                {artifact.is_draft ? 'Draft' : 'Final'}
              </Badge>
              <span className="text-sm text-gray-500">
                v{artifact.version} • {formatDate(artifact.updated_at)}
              </span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 ml-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="flex items-center gap-2"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  Copy
                </>
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              className="flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              Download
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="ml-2"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderContent()}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50">
          <p className="text-xs text-gray-500 text-center">
            {artifact.created_by === 'agent' ? 'Generated by Krystal Le Agent' : `Created by ${artifact.created_by}`}
          </p>
        </div>
      </div>
    </div>
  );
}

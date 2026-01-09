'use client';

import { useState } from 'react';
import {
  X,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Download,
  FileText,
} from 'lucide-react';
import { Button, Badge } from '@/components/ui';
import type { Document } from '@/lib/api';

interface DocumentViewerProps {
  document: Document;
  onClose: () => void;
  highlightPages?: number[];
}

export function DocumentViewer({
  document,
  onClose,
  highlightPages = [],
}: DocumentViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  const totalPages = document.page_count || 1;

  const goToPrevPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1));
  };

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(200, prev + 25));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(50, prev - 25));
  };

  // PDF viewer URL (would need to be implemented with actual presigned URLs)
  const pdfUrl = `/api/documents/${document.id}/view`;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between bg-gray-800 px-4 py-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onClose} className="text-white">
            <X className="h-5 w-5" />
          </Button>
          <div>
            <h2 className="font-medium text-white">{document.filename}</h2>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              {document.is_ocr && (
                <Badge variant="secondary" className="text-xs">
                  OCR
                </Badge>
              )}
              {document.tags?.map((tag) => (
                <Badge key={tag} variant="default" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleZoomOut}
            className="text-white"
            disabled={zoom <= 50}
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="min-w-[60px] text-center text-sm text-white">
            {zoom}%
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleZoomIn}
            className="text-white"
            disabled={zoom >= 200}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>

          <div className="mx-2 h-6 w-px bg-gray-700" />

          {/* Download */}
          <Button variant="ghost" size="sm" className="text-white">
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Document content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main viewer */}
        <div className="flex-1 overflow-auto bg-gray-700 p-8">
          <div
            className="mx-auto bg-white shadow-2xl"
            style={{
              width: `${(8.5 * 96 * zoom) / 100}px`,
              minHeight: `${(11 * 96 * zoom) / 100}px`,
            }}
          >
            {/* Placeholder for actual PDF rendering */}
            <div className="flex h-full min-h-[800px] items-center justify-center">
              <div className="text-center text-gray-400">
                <FileText className="mx-auto h-16 w-16 text-gray-300" />
                <p className="mt-4 text-lg">Document Viewer</p>
                <p className="mt-2 text-sm">
                  PDF rendering would be implemented here using react-pdf
                </p>
                <p className="mt-4 text-xs text-gray-500">
                  Page {currentPage} of {totalPages}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Page thumbnails sidebar */}
        {totalPages > 1 && (
          <div className="w-48 overflow-y-auto bg-gray-800 p-4">
            <p className="mb-3 text-xs font-medium uppercase text-gray-400">
              Pages
            </p>
            <div className="space-y-2">
              {Array.from({ length: Math.min(totalPages, 50) }, (_, i) => i + 1).map(
                (page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`w-full rounded border-2 p-2 text-left text-xs transition-colors ${
                      currentPage === page
                        ? 'border-primary-500 bg-gray-700'
                        : highlightPages.includes(page)
                          ? 'border-yellow-500 bg-yellow-900/20'
                          : 'border-transparent bg-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <div className="aspect-[8.5/11] rounded bg-gray-600" />
                    <p className="mt-1 text-center text-gray-300">
                      {page}
                      {highlightPages.includes(page) && (
                        <span className="ml-1 text-yellow-500">*</span>
                      )}
                    </p>
                  </button>
                )
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer with page navigation */}
      <div className="flex items-center justify-center gap-4 bg-gray-800 py-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={goToPrevPage}
          disabled={currentPage <= 1}
          className="text-white"
        >
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <span className="text-sm text-white">
          Page {currentPage} of {totalPages}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={goToNextPage}
          disabled={currentPage >= totalPages}
          className="text-white"
        >
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search, Filter, Briefcase } from 'lucide-react';
import { Button, Input, Card, Badge } from '@/components/ui';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
  open: 'default',
  in_progress: 'default',
  pending_review: 'warning',
  needs_info: 'error',
  completed: 'success',
  closed: 'secondary',
};

export default function CasesPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { data: cases, isLoading } = useQuery({
    queryKey: ['cases', statusFilter],
    queryFn: () => api.getCases(statusFilter ? { status: statusFilter } : undefined),
  });

  const filteredCases = cases?.filter((c) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      c.client?.name?.toLowerCase().includes(searchLower) ||
      c.client?.client_code?.toLowerCase().includes(searchLower) ||
      c.case_type.toLowerCase().includes(searchLower)
    );
  });

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cases</h1>
          <p className="text-gray-600">Manage client cases and tax returns</p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Case
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search cases..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="pending_review">Pending Review</option>
          <option value="needs_info">Needs Info</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {/* Cases List */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-500">Loading cases...</div>
      ) : filteredCases && filteredCases.length > 0 ? (
        <div className="grid gap-4">
          {filteredCases.map((caseItem) => (
            <Link key={caseItem.id} href={`/cases/${caseItem.id}`}>
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <div className="flex items-center justify-between p-6">
                  <div className="flex items-center gap-4">
                    <div className="rounded-lg bg-primary-100 p-3">
                      <Briefcase className="h-6 w-6 text-primary-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">
                        {caseItem.client?.name || 'Unknown Client'}
                      </p>
                      <p className="text-sm text-gray-600">
                        {caseItem.client?.client_code} &bull; {caseItem.case_type}{' '}
                        &bull; {caseItem.year}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant={statusColors[caseItem.status] || 'default'}>
                      {caseItem.status.replace('_', ' ')}
                    </Badge>
                    <p className="text-sm text-gray-500">
                      {formatDate(caseItem.updated_at)}
                    </p>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card>
          <div className="py-12 text-center">
            <Briefcase className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No cases found</h3>
            <p className="mt-2 text-sm text-gray-500">
              {search
                ? 'Try adjusting your search or filters'
                : 'Get started by creating your first case'}
            </p>
            {!search && (
              <Button className="mt-4">
                <Plus className="mr-2 h-4 w-4" />
                New Case
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

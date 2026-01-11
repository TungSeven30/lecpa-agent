'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search, Briefcase } from 'lucide-react';
import { Button, Input, Card, Badge } from '@/components/ui';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';

type BadgeVariant = 'default' | 'secondary' | 'success' | 'warning' | 'error' | 'info';

const statusColors: Record<string, BadgeVariant> = {
    open: 'info',
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
        queryFn: () =>
            api.getCases(statusFilter ? { status: statusFilter } : undefined),
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
                    <h1 className="text-2xl font-bold text-foreground">Cases</h1>
                    <p className="text-muted-foreground">
                        Manage client cases and tax returns
                    </p>
                </div>
                <Button>
                    <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                    New Case
                </Button>
            </div>

            {/* Filters */}
            <div className="mb-6 flex gap-4">
                <div className="relative flex-1">
                    <Search
                        className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                        aria-hidden="true"
                    />
                    <Input
                        placeholder="Search cases..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-10"
                        aria-label="Search cases"
                    />
                </div>
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="min-h-[44px] rounded-md border border-input bg-background px-4 py-2 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    aria-label="Filter by status"
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
                <div className="py-12 text-center text-muted-foreground">
                    Loading cases...
                </div>
            ) : filteredCases && filteredCases.length > 0 ? (
                <div className="grid gap-4">
                    {filteredCases.map((caseItem) => (
                        <Link key={caseItem.id} href={`/cases/${caseItem.id}`}>
                            <Card className="cursor-pointer transition-shadow hover:shadow-md">
                                <div className="flex items-center justify-between p-6">
                                    <div className="flex items-center gap-4">
                                        <div className="rounded-lg bg-primary-100 p-3 dark:bg-primary-900">
                                            <Briefcase
                                                className="h-6 w-6 text-primary-600 dark:text-primary-400"
                                                aria-hidden="true"
                                            />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground">
                                                {caseItem.client?.name || 'Unknown Client'}
                                            </p>
                                            <p className="text-sm text-muted-foreground">
                                                {caseItem.client?.client_code} &bull;{' '}
                                                {caseItem.case_type} &bull; {caseItem.year}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <Badge
                                            variant={statusColors[caseItem.status] || 'default'}
                                        >
                                            {caseItem.status.replace(/_/g, ' ')}
                                        </Badge>
                                        <p className="text-sm text-muted-foreground">
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
                        <Briefcase
                            className="mx-auto h-12 w-12 text-muted-foreground"
                            aria-hidden="true"
                        />
                        <h3 className="mt-4 text-lg font-medium text-foreground">
                            No cases found
                        </h3>
                        <p className="mt-2 text-sm text-muted-foreground">
                            {search
                                ? 'Try adjusting your search or filters'
                                : 'Get started by creating your first case'}
                        </p>
                        {!search && (
                            <Button className="mt-4">
                                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                                New Case
                            </Button>
                        )}
                    </div>
                </Card>
            )}
        </div>
    );
}

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search, Briefcase, ChevronRight } from 'lucide-react';
import { Button, Input, Card, Badge, Skeleton } from '@/components/ui';
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

function CaseCardSkeleton() {
    return (
        <Card>
            <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-12 w-12 rounded-lg" />
                    <div className="space-y-2">
                        <Skeleton className="h-4 w-40" />
                        <Skeleton className="h-3 w-32" />
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <Skeleton className="h-5 w-20 rounded-full" />
                    <Skeleton className="h-4 w-24" />
                </div>
            </div>
        </Card>
    );
}

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
        <div className="p-6 lg:p-8">
            <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-foreground">Cases</h1>
                    <p className="mt-1 text-muted-foreground">
                        Manage client cases and tax returns
                    </p>
                </div>
                <Button>
                    <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                    New Case
                </Button>
            </div>

            {/* Filters */}
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:gap-4">
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
                    className="min-h-[44px] rounded-md border border-input bg-background px-4 py-2 text-sm text-foreground transition-colors focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
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
                <div className="grid gap-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <CaseCardSkeleton key={i} />
                    ))}
                </div>
            ) : filteredCases && filteredCases.length > 0 ? (
                <div className="grid gap-3">
                    {filteredCases.map((caseItem) => (
                        <Link
                            key={caseItem.id}
                            href={`/cases/${caseItem.id}`}
                            className="group"
                        >
                            <Card className="transition-all duration-200 group-hover:shadow-md group-hover:border-primary-200 dark:group-hover:border-primary-800">
                                <div className="flex items-center justify-between p-5">
                                    <div className="flex items-center gap-4">
                                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 transition-colors group-hover:bg-primary-200 dark:bg-primary-900 dark:group-hover:bg-primary-800">
                                            <Briefcase
                                                className="h-6 w-6 text-primary-600 dark:text-primary-400"
                                                aria-hidden="true"
                                            />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground">
                                                {caseItem.client?.name || 'Unknown Client'}
                                            </p>
                                            <p className="mt-0.5 text-sm text-muted-foreground">
                                                {caseItem.client?.client_code} · {caseItem.case_type} ·{' '}
                                                {caseItem.year}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Badge
                                            variant={statusColors[caseItem.status] || 'default'}
                                        >
                                            {caseItem.status.replace(/_/g, ' ')}
                                        </Badge>
                                        <span className="hidden text-sm text-muted-foreground sm:inline">
                                            {formatDate(caseItem.updated_at)}
                                        </span>
                                        <ChevronRight
                                            className="h-5 w-5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                                            aria-hidden="true"
                                        />
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>
            ) : (
                <Card>
                    <div className="py-16 text-center">
                        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                            <Briefcase
                                className="h-8 w-8 text-muted-foreground"
                                aria-hidden="true"
                            />
                        </div>
                        <h3 className="mt-4 text-lg font-medium text-foreground">
                            No cases found
                        </h3>
                        <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
                            {search
                                ? 'Try adjusting your search or filters'
                                : 'Get started by creating your first case'}
                        </p>
                        {!search && (
                            <Button className="mt-6">
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

'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
    Briefcase,
    FileText,
    MessageSquare,
    Clock,
    AlertCircle,
    ChevronRight,
} from 'lucide-react';
import { Card, CardContent, Badge, Skeleton } from '@/components/ui';
import { api } from '@/lib/api';

interface Stat {
    name: string;
    value: number | string;
    icon: typeof Briefcase;
    iconClasses: string;
}

export default function DashboardPage() {
    const { data: cases, isLoading: casesLoading } = useQuery({
        queryKey: ['cases'],
        queryFn: () => api.getCases({ status: 'open' }),
    });

    const stats: Stat[] = [
        {
            name: 'Open Cases',
            value: cases?.length || 0,
            icon: Briefcase,
            iconClasses: 'bg-info text-info-foreground',
        },
        {
            name: 'Documents',
            value: '-',
            icon: FileText,
            iconClasses: 'bg-success text-success-foreground',
        },
        {
            name: 'Pending Review',
            value: cases?.filter((c) => c.status === 'pending_review').length || 0,
            icon: Clock,
            iconClasses: 'bg-warning text-warning-foreground',
        },
        {
            name: 'Needs Attention',
            value: cases?.filter((c) => c.status === 'needs_info').length || 0,
            icon: AlertCircle,
            iconClasses: 'bg-error text-error-foreground',
        },
    ];

    const getStatusBadgeVariant = (
        status: string
    ): 'success' | 'warning' | 'secondary' => {
        switch (status) {
            case 'open':
                return 'success';
            case 'pending_review':
                return 'warning';
            default:
                return 'secondary';
        }
    };

    return (
        <div className="p-6 lg:p-8">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
                <p className="mt-1 text-muted-foreground">
                    Welcome back to Le CPA Agent
                </p>
            </div>

            {/* Stats Grid */}
            <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
                {stats.map((stat) => (
                    <Card
                        key={stat.name}
                        className="transition-shadow duration-200 hover:shadow-md"
                    >
                        <CardContent className="p-5">
                            <div className="flex items-center">
                                <div
                                    className={`flex h-12 w-12 items-center justify-center rounded-lg ${stat.iconClasses}`}
                                >
                                    <stat.icon className="h-6 w-6" aria-hidden="true" />
                                </div>
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-muted-foreground">
                                        {stat.name}
                                    </p>
                                    {casesLoading ? (
                                        <Skeleton className="mt-1 h-7 w-10" />
                                    ) : (
                                        <p className="text-2xl font-semibold tabular-nums text-foreground">
                                            {stat.value}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Quick Actions */}
            <div className="mb-8">
                <h2 className="mb-4 text-lg font-semibold text-foreground">
                    Quick Actions
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <Link href="/chat" className="group">
                        <Card className="h-full transition-all duration-200 group-hover:shadow-md group-hover:border-primary-200 dark:group-hover:border-primary-800">
                            <CardContent className="flex items-center p-5">
                                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 text-primary-600 transition-colors group-hover:bg-primary-200 dark:bg-primary-900 dark:text-primary-400 dark:group-hover:bg-primary-800">
                                    <MessageSquare className="h-6 w-6" aria-hidden="true" />
                                </div>
                                <div className="ml-4 flex-1">
                                    <p className="font-medium text-foreground">Start Chat</p>
                                    <p className="mt-0.5 text-sm text-muted-foreground">
                                        Ask questions about clients
                                    </p>
                                </div>
                                <ChevronRight
                                    className="h-5 w-5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                                    aria-hidden="true"
                                />
                            </CardContent>
                        </Card>
                    </Link>
                    <Link href="/cases" className="group">
                        <Card className="h-full transition-all duration-200 group-hover:shadow-md group-hover:border-primary-200 dark:group-hover:border-primary-800">
                            <CardContent className="flex items-center p-5">
                                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 text-primary-600 transition-colors group-hover:bg-primary-200 dark:bg-primary-900 dark:text-primary-400 dark:group-hover:bg-primary-800">
                                    <Briefcase className="h-6 w-6" aria-hidden="true" />
                                </div>
                                <div className="ml-4 flex-1">
                                    <p className="font-medium text-foreground">View Cases</p>
                                    <p className="mt-0.5 text-sm text-muted-foreground">
                                        Browse and manage cases
                                    </p>
                                </div>
                                <ChevronRight
                                    className="h-5 w-5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                                    aria-hidden="true"
                                />
                            </CardContent>
                        </Card>
                    </Link>
                    <Link href="/cases?new=true" className="group">
                        <Card className="h-full transition-all duration-200 group-hover:shadow-md group-hover:border-primary-200 dark:group-hover:border-primary-800">
                            <CardContent className="flex items-center p-5">
                                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 text-primary-600 transition-colors group-hover:bg-primary-200 dark:bg-primary-900 dark:text-primary-400 dark:group-hover:bg-primary-800">
                                    <FileText className="h-6 w-6" aria-hidden="true" />
                                </div>
                                <div className="ml-4 flex-1">
                                    <p className="font-medium text-foreground">New Case</p>
                                    <p className="mt-0.5 text-sm text-muted-foreground">
                                        Create a new client case
                                    </p>
                                </div>
                                <ChevronRight
                                    className="h-5 w-5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                                    aria-hidden="true"
                                />
                            </CardContent>
                        </Card>
                    </Link>
                </div>
            </div>

            {/* Recent Cases */}
            <div>
                <h2 className="mb-4 text-lg font-semibold text-foreground">
                    Recent Cases
                </h2>
                <Card>
                    <div className="divide-y divide-border">
                        {casesLoading ? (
                            // Skeleton loading state
                            Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="flex items-center justify-between p-4">
                                    <div className="space-y-2">
                                        <Skeleton className="h-4 w-40" />
                                        <Skeleton className="h-3 w-24" />
                                    </div>
                                    <Skeleton className="h-5 w-16 rounded-full" />
                                </div>
                            ))
                        ) : cases && cases.length > 0 ? (
                            cases.slice(0, 5).map((caseItem) => (
                                <Link
                                    key={caseItem.id}
                                    href={`/cases/${caseItem.id}`}
                                    className="flex items-center justify-between p-4 transition-colors duration-150 hover:bg-accent"
                                >
                                    <div>
                                        <p className="font-medium text-foreground">
                                            {caseItem.client?.name || 'Unknown Client'}
                                        </p>
                                        <p className="mt-0.5 text-sm text-muted-foreground">
                                            {caseItem.case_type} · {caseItem.year}
                                        </p>
                                    </div>
                                    <Badge variant={getStatusBadgeVariant(caseItem.status)}>
                                        {caseItem.status.replace(/_/g, ' ')}
                                    </Badge>
                                </Link>
                            ))
                        ) : (
                            <div className="py-12 text-center">
                                <Briefcase
                                    className="mx-auto h-10 w-10 text-muted-foreground/50"
                                    aria-hidden="true"
                                />
                                <p className="mt-3 text-sm text-muted-foreground">
                                    No cases found
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground/75">
                                    Create your first case to get started
                                </p>
                            </div>
                        )}
                    </div>
                </Card>
            </div>
        </div>
    );
}

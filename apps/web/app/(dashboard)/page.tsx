'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
    Briefcase,
    FileText,
    MessageSquare,
    Clock,
    AlertCircle,
} from 'lucide-react';
import { Card, CardContent, Badge } from '@/components/ui';
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
        <div className="p-8">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
                <p className="text-muted-foreground">
                    Welcome back to Le CPA Agent
                </p>
            </div>

            {/* Stats Grid */}
            <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {stats.map((stat) => (
                    <Card key={stat.name}>
                        <CardContent className="p-6">
                            <div className="flex items-center">
                                <div className={`rounded-lg p-3 ${stat.iconClasses}`}>
                                    <stat.icon className="h-6 w-6" aria-hidden="true" />
                                </div>
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-muted-foreground">
                                        {stat.name}
                                    </p>
                                    <p className="text-2xl font-semibold text-foreground">
                                        {casesLoading ? '...' : stat.value}
                                    </p>
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
                    <Link href="/chat">
                        <Card className="cursor-pointer transition-shadow hover:shadow-md">
                            <CardContent className="flex items-center p-6">
                                <MessageSquare
                                    className="h-8 w-8 text-primary-600"
                                    aria-hidden="true"
                                />
                                <div className="ml-4">
                                    <p className="font-medium text-foreground">Start Chat</p>
                                    <p className="text-sm text-muted-foreground">
                                        Ask questions about clients or documents
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                    <Link href="/cases">
                        <Card className="cursor-pointer transition-shadow hover:shadow-md">
                            <CardContent className="flex items-center p-6">
                                <Briefcase
                                    className="h-8 w-8 text-primary-600"
                                    aria-hidden="true"
                                />
                                <div className="ml-4">
                                    <p className="font-medium text-foreground">View Cases</p>
                                    <p className="text-sm text-muted-foreground">
                                        Browse and manage client cases
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                    <Link href="/cases?new=true">
                        <Card className="cursor-pointer transition-shadow hover:shadow-md">
                            <CardContent className="flex items-center p-6">
                                <FileText
                                    className="h-8 w-8 text-primary-600"
                                    aria-hidden="true"
                                />
                                <div className="ml-4">
                                    <p className="font-medium text-foreground">New Case</p>
                                    <p className="text-sm text-muted-foreground">
                                        Create a new client case
                                    </p>
                                </div>
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
                            <div className="p-6 text-center text-muted-foreground">
                                Loading...
                            </div>
                        ) : cases && cases.length > 0 ? (
                            cases.slice(0, 5).map((caseItem) => (
                                <Link
                                    key={caseItem.id}
                                    href={`/cases/${caseItem.id}`}
                                    className="block p-4 hover:bg-accent"
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="font-medium text-foreground">
                                                {caseItem.client?.name || 'Unknown Client'}
                                            </p>
                                            <p className="text-sm text-muted-foreground">
                                                {caseItem.case_type} - {caseItem.year}
                                            </p>
                                        </div>
                                        <Badge variant={getStatusBadgeVariant(caseItem.status)}>
                                            {caseItem.status.replace(/_/g, ' ')}
                                        </Badge>
                                    </div>
                                </Link>
                            ))
                        ) : (
                            <div className="p-6 text-center text-muted-foreground">
                                No cases found. Create your first case to get started.
                            </div>
                        )}
                    </div>
                </Card>
            </div>
        </div>
    );
}

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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { api } from '@/lib/api';

export default function DashboardPage() {
  const { data: cases, isLoading: casesLoading } = useQuery({
    queryKey: ['cases'],
    queryFn: () => api.getCases({ status: 'open' }),
  });

  const stats = [
    {
      name: 'Open Cases',
      value: cases?.length || 0,
      icon: Briefcase,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      name: 'Documents',
      value: '-',
      icon: FileText,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      name: 'Pending Review',
      value: cases?.filter((c) => c.status === 'pending_review').length || 0,
      icon: Clock,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
    },
    {
      name: 'Needs Attention',
      value: cases?.filter((c) => c.status === 'needs_info').length || 0,
      icon: AlertCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
    },
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Welcome back to Krystal Le Agent</p>
      </div>

      {/* Stats Grid */}
      <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardContent className="p-6">
              <div className="flex items-center">
                <div className={`rounded-lg p-3 ${stat.bgColor}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">
                    {stat.name}
                  </p>
                  <p className="text-2xl font-semibold text-gray-900">
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
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Link href="/chat">
            <Card className="cursor-pointer transition-shadow hover:shadow-md">
              <CardContent className="flex items-center p-6">
                <MessageSquare className="h-8 w-8 text-primary-600" />
                <div className="ml-4">
                  <p className="font-medium text-gray-900">Start Chat</p>
                  <p className="text-sm text-gray-600">
                    Ask questions about clients or documents
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>
          <Link href="/cases">
            <Card className="cursor-pointer transition-shadow hover:shadow-md">
              <CardContent className="flex items-center p-6">
                <Briefcase className="h-8 w-8 text-primary-600" />
                <div className="ml-4">
                  <p className="font-medium text-gray-900">View Cases</p>
                  <p className="text-sm text-gray-600">
                    Browse and manage client cases
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>
          <Link href="/cases?new=true">
            <Card className="cursor-pointer transition-shadow hover:shadow-md">
              <CardContent className="flex items-center p-6">
                <FileText className="h-8 w-8 text-primary-600" />
                <div className="ml-4">
                  <p className="font-medium text-gray-900">New Case</p>
                  <p className="text-sm text-gray-600">
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
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Recent Cases
        </h2>
        <Card>
          <div className="divide-y">
            {casesLoading ? (
              <div className="p-6 text-center text-gray-500">Loading...</div>
            ) : cases && cases.length > 0 ? (
              cases.slice(0, 5).map((caseItem) => (
                <Link
                  key={caseItem.id}
                  href={`/cases/${caseItem.id}`}
                  className="block p-4 hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">
                        {caseItem.client?.name || 'Unknown Client'}
                      </p>
                      <p className="text-sm text-gray-600">
                        {caseItem.case_type} - {caseItem.year}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        caseItem.status === 'open'
                          ? 'bg-green-100 text-green-800'
                          : caseItem.status === 'pending_review'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {caseItem.status}
                    </span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="p-6 text-center text-gray-500">
                No cases found. Create your first case to get started.
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

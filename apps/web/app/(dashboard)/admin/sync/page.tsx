'use client';

import { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Skeleton,
} from '@/components/ui';
import {
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  FileText,
  Building2,
  User,
  AlertCircle,
} from 'lucide-react';

interface QueueItem {
  id: string;
  item_type: 'client' | 'case';
  nas_path: string;
  parsed_data: {
    client_code: string;
    client_name?: string;
    client_type?: string;
    year?: number;
  };
  status: string;
  created_at: string;
  auto_approve_at?: string;
}

interface SyncStatus {
  agent_status: string;
  last_heartbeat: string | null;
  last_file_event: string | null;
  queue_stats: {
    pending_approval: number;
    processing: number;
    failed_today: number;
  };
  today_stats: {
    files_detected: number;
    files_processed: number;
    files_failed: number;
  };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function SyncAdminPage() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [statusRes, queueRes] = await Promise.all([
        fetch(`${API_BASE}/ingest/sync-status`),
        fetch(`${API_BASE}/ingest/sync-queue?status=pending`),
      ]);

      if (!statusRes.ok || !queueRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const statusData = await statusRes.json();
      const queueData = await queueRes.json();

      setStatus(statusData);
      setQueue(queueData.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (id: string) => {
    setActionLoading(id);
    try {
      const res = await fetch(`${API_BASE}/ingest/sync-queue/${id}/approve`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to approve');
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve item');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: string) => {
    setActionLoading(id);
    try {
      const res = await fetch(`${API_BASE}/ingest/sync-queue/${id}/reject`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to reject');
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject item');
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadgeVariant = (agentStatus: string) => {
    switch (agentStatus) {
      case 'healthy':
        return 'default';
      case 'stale':
        return 'secondary';
      default:
        return 'destructive';
    }
  };

  const formatTimeAgo = (dateString: string | null) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <h1 className="text-2xl font-bold">NAS Sync Management</h1>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">NAS Sync Management</h1>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive p-4 rounded-md flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Agent Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={getStatusBadgeVariant(status?.agent_status || 'disconnected')}>
              {status?.agent_status || 'Unknown'}
            </Badge>
            <p className="text-xs text-muted-foreground mt-2">
              Last heartbeat: {formatTimeAgo(status?.last_heartbeat || null)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pending Approval
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">
              {status?.queue_stats?.pending_approval || 0}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Files Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">
              {status?.today_stats?.files_processed || 0}
            </span>
            <span className="text-muted-foreground text-sm ml-1">
              / {status?.today_stats?.files_detected || 0}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Failed Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold text-destructive">
              {status?.today_stats?.files_failed || 0}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Approval Queue */}
      <Card>
        <CardHeader>
          <CardTitle>Approval Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {queue.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No items pending approval</p>
            </div>
          ) : (
            <div className="space-y-4">
              {queue.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    {item.item_type === 'client' ? (
                      item.parsed_data.client_type === 'business' ? (
                        <Building2 className="h-5 w-5 text-muted-foreground" />
                      ) : (
                        <User className="h-5 w-5 text-muted-foreground" />
                      )
                    ) : (
                      <FileText className="h-5 w-5 text-muted-foreground" />
                    )}

                    <div>
                      <p className="font-medium">
                        {item.parsed_data.client_code}
                        {item.parsed_data.client_name && ` - ${item.parsed_data.client_name}`}
                      </p>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                          {item.item_type}
                        </Badge>
                        {item.item_type === 'case' && item.parsed_data.year && (
                          <span className="text-sm text-muted-foreground">
                            Year: {item.parsed_data.year}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground truncate max-w-md mt-1">
                        {item.nas_path}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {item.auto_approve_at && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Auto: {new Date(item.auto_approve_at).toLocaleTimeString()}
                      </span>
                    )}

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleApprove(item.id)}
                      disabled={actionLoading === item.id}
                    >
                      <CheckCircle className="h-4 w-4 mr-1" />
                      Approve
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleReject(item.id)}
                      disabled={actionLoading === item.id}
                    >
                      <XCircle className="h-4 w-4 mr-1" />
                      Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Sync Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Last File Event</p>
              <p className="font-medium">
                {formatTimeAgo(status?.last_file_event || null)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Processing Queue</p>
              <p className="font-medium">
                {status?.queue_stats?.processing || 0} documents
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

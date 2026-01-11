'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from 'next-auth/react';
import { useState } from 'react';
import { ToastProvider } from '@/components/ui/toast';
import { ThemeProbe } from '@/components/debug/theme-probe';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <ThemeProbe label="root-providers" />
          {children}
        </ToastProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}

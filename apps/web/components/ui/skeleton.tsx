'use client';

import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
    /**
     * Whether to animate the skeleton with a shimmer effect.
     * @default true
     */
    animate?: boolean;
}

/**
 * Skeleton loading placeholder component.
 *
 * Provides visual feedback during content loading with an animated shimmer effect.
 * Respects reduced motion preferences.
 */
export function Skeleton({ className, animate = true, ...props }: SkeletonProps) {
    return (
        <div
            className={cn(
                'rounded-md bg-muted',
                animate && 'animate-pulse motion-reduce:animate-none',
                className
            )}
            aria-hidden="true"
            {...props}
        />
    );
}

/**
 * Pre-built skeleton for card content.
 */
export function CardSkeleton() {
    return (
        <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-center gap-4">
                <Skeleton className="h-12 w-12 rounded-lg" />
                <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                </div>
            </div>
        </div>
    );
}

/**
 * Pre-built skeleton for list items.
 */
export function ListItemSkeleton() {
    return (
        <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-24" />
                </div>
            </div>
            <Skeleton className="h-6 w-16 rounded-full" />
        </div>
    );
}

/**
 * Pre-built skeleton for stat cards.
 */
export function StatCardSkeleton() {
    return (
        <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-center">
                <Skeleton className="h-12 w-12 rounded-lg" />
                <div className="ml-4 space-y-2">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-6 w-12" />
                </div>
            </div>
        </div>
    );
}

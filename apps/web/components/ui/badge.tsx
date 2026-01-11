'use client';

import { cn } from '@/lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'default' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
}

/**
 * Badge component for status indicators and labels.
 *
 * Uses semantic color tokens that support dark mode.
 *
 * Args:
 *     variant: Visual style - default (primary), secondary (muted), or status colors
 */
export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
    const variantStyles = {
        default: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200',
        secondary: 'bg-muted text-muted-foreground',
        success: 'bg-success text-success-foreground',
        warning: 'bg-warning text-warning-foreground',
        error: 'bg-error text-error-foreground',
        info: 'bg-info text-info-foreground',
    };

    return (
        <span
            className={cn(
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                variantStyles[variant],
                className
            )}
            {...props}
        />
    );
}

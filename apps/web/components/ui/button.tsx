'use client';

import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'default' | 'outline' | 'ghost' | 'destructive';
    size?: 'sm' | 'md' | 'lg';
    isLoading?: boolean;
}

/**
 * Button component with multiple variants and sizes.
 *
 * Supports loading state and is fully accessible with proper focus indicators.
 * All sizes meet minimum 44px touch target requirements.
 *
 * Args:
 *     variant: Visual style - default, outline, ghost, or destructive
 *     size: Size variant - sm, md, or lg
 *     isLoading: Whether to show loading spinner
 *     disabled: Whether button is disabled
 *     children: Button content
 */
const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            className,
            variant = 'default',
            size = 'md',
            isLoading,
            disabled,
            children,
            ...props
        },
        ref
    ) => {
        const baseStyles =
            'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

        const variants = {
            default: 'bg-primary-600 text-white hover:bg-primary-700',
            outline:
                'border border-gray-300 bg-white hover:bg-gray-100 text-gray-900',
            ghost: 'hover:bg-gray-100 text-gray-700',
            destructive: 'bg-red-600 text-white hover:bg-red-700',
        };

        // All sizes meet 44px minimum touch target
        const sizes = {
            sm: 'min-h-[44px] px-3 text-sm',
            md: 'min-h-[44px] px-4 text-sm',
            lg: 'min-h-[48px] px-6 text-base',
        };

        return (
            <button
                className={cn(baseStyles, variants[variant], sizes[size], className)}
                ref={ref}
                disabled={disabled || isLoading}
                aria-disabled={disabled || isLoading}
                {...props}
            >
                {isLoading ? (
                    <>
                        <svg
                            className="mr-2 h-4 w-4 animate-spin"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                        >
                            <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                            />
                            <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                        </svg>
                        <span>Loading...</span>
                    </>
                ) : (
                    children
                )}
            </button>
        );
    }
);

Button.displayName = 'Button';

export { Button };

'use client';

import { forwardRef, useId } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
    extends React.InputHTMLAttributes<HTMLInputElement> {
    error?: string;
    label?: string;
}

/**
 * Input component with error state and optional label.
 *
 * Accessible with proper focus indicators and error messaging.
 *
 * Args:
 *     error: Error message to display below input
 *     label: Optional label text (for accessibility)
 *     type: Input type (text, email, password, etc.)
 */
const Input = forwardRef<HTMLInputElement, InputProps>(
    ({ className, type, error, label, id, ...props }, ref) => {
        const generatedId = useId();
        const inputId = id || generatedId;
        const errorId = error ? `${inputId}-error` : undefined;

        return (
            <div className="w-full">
                {label && (
                    <label
                        htmlFor={inputId}
                        className="mb-1 block text-sm font-medium text-gray-700"
                    >
                        {label}
                    </label>
                )}
                <input
                    id={inputId}
                    type={type}
                    className={cn(
                        'flex min-h-[44px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 file:border-0 file:bg-transparent file:text-sm file:font-medium',
                        error && 'border-red-500 focus-visible:ring-red-500',
                        className
                    )}
                    ref={ref}
                    aria-invalid={error ? 'true' : undefined}
                    aria-describedby={errorId}
                    {...props}
                />
                {error && (
                    <p id={errorId} className="mt-1 text-sm text-red-600" role="alert">
                        {error}
                    </p>
                )}
            </div>
        );
    }
);

Input.displayName = 'Input';

export { Input };

'use client';

import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './button';

interface ErrorBoundaryProps {
    children: ReactNode;
    fallback?: ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

/**
 * Error boundary component to catch and handle React errors gracefully.
 *
 * Prevents the entire app from crashing when a component throws an error.
 * Displays a user-friendly error message with retry functionality.
 *
 * Args:
 *     children: Child components to wrap and protect
 *     fallback: Optional custom fallback UI to display on error
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
        // Log error for debugging/monitoring
        console.error('Error boundary caught:', error, errorInfo);
    }

    handleRetry = (): void => {
        this.setState({ hasError: false, error: null });
    };

    render(): ReactNode {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div
                    role="alert"
                    className="flex flex-col items-center justify-center p-8 text-center"
                >
                    <div className="rounded-full bg-red-100 p-4">
                        <AlertTriangle
                            className="h-8 w-8 text-red-600"
                            aria-hidden="true"
                        />
                    </div>
                    <h2 className="mt-4 text-lg font-semibold text-gray-900">
                        Something went wrong
                    </h2>
                    <p className="mt-2 max-w-md text-sm text-gray-600">
                        An unexpected error occurred. Please try again or contact support
                        if the problem persists.
                    </p>
                    <Button onClick={this.handleRetry} className="mt-4">
                        <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                        Try again
                    </Button>
                </div>
            );
        }

        return this.props.children;
    }
}

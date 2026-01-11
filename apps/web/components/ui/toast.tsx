'use client';

import { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
    id: string;
    message: string;
    type: ToastType;
}

interface ToastContextType {
    showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

/**
 * Hook to access toast notifications.
 *
 * Must be used within a ToastProvider.
 *
 * Returns:
 *     Object with showToast function to display notifications
 *
 * Raises:
 *     Error: If used outside of ToastProvider
 */
export function useToast(): ToastContextType {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
}

interface ToastProviderProps {
    children: React.ReactNode;
}

/**
 * Provider component for toast notifications.
 *
 * Wraps the application to enable toast notifications throughout.
 * Renders a fixed-position container for toast messages with auto-dismiss.
 *
 * Args:
 *     children: Child components to wrap
 */
export function ToastProvider({ children }: ToastProviderProps) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const showToast = useCallback((message: string, type: ToastType = 'info') => {
        const id = crypto.randomUUID();
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 3000);
    }, []);

    const dismissToast = (id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    const icons = {
        success: CheckCircle,
        error: AlertCircle,
        info: Info,
    };

    const styles = {
        success: 'bg-green-50 border-green-200 text-green-800',
        error: 'bg-red-50 border-red-200 text-red-800',
        info: 'bg-blue-50 border-blue-200 text-blue-800',
    };

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            <div
                aria-live="polite"
                aria-label="Notifications"
                className="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
            >
                {toasts.map((toast) => {
                    const Icon = icons[toast.type];
                    return (
                        <div
                            key={toast.id}
                            role="alert"
                            className={cn(
                                'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg',
                                'transition-all duration-200 ease-out',
                                styles[toast.type]
                            )}
                        >
                            <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                            <p className="text-sm font-medium">{toast.message}</p>
                            <button
                                onClick={() => dismissToast(toast.id)}
                                className="ml-2 rounded p-1.5 hover:bg-black/5 min-h-[44px] min-w-[44px] flex items-center justify-center -mr-2"
                                aria-label="Dismiss notification"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                    );
                })}
            </div>
        </ToastContext.Provider>
    );
}

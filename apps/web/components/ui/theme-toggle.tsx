'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { Button } from './button';
import { cn } from '@/lib/utils';

interface ThemeToggleProps {
    className?: string;
}

/**
 * Theme toggle button for switching between light and dark modes.
 *
 * Persists preference to localStorage and respects system preference on first load.
 */
export function ThemeToggle({ className }: ThemeToggleProps) {
    const [theme, setTheme] = useState<'light' | 'dark'>('light');
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        // Check localStorage first, then system preference
        const stored = localStorage.getItem('theme');
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/5937626b-a57e-4319-a3b8-d487f9ec7f14', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sessionId: 'debug-session',
                runId: 'pre-fix',
                hypothesisId: 'C',
                location: 'components/ui/theme-toggle.tsx:28',
                message: 'ThemeToggle init',
                data: {
                    stored,
                    prefersDark:
                        window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ?? null,
                    initialHtmlClass: document.documentElement.className,
                },
                timestamp: Date.now(),
            }),
        }).catch(() => {});
        // #endregion agent log
        if (stored === 'dark' || stored === 'light') {
            setTheme(stored);
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setTheme('dark');
        }
    }, []);

    useEffect(() => {
        if (!mounted) return;

        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);

        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/5937626b-a57e-4319-a3b8-d487f9ec7f14', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sessionId: 'debug-session',
                runId: 'pre-fix',
                hypothesisId: 'C',
                location: 'components/ui/theme-toggle.tsx:64',
                message: 'ThemeToggle applied',
                data: {
                    theme,
                    htmlClass: root.className,
                    hasDark: root.classList.contains('dark'),
                },
                timestamp: Date.now(),
            }),
        }).catch(() => {});
        // #endregion agent log
    }, [theme, mounted]);

    const toggleTheme = () => {
        setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
    };

    // Prevent hydration mismatch
    if (!mounted) {
        return (
            <Button variant="ghost" size="sm" className={cn("min-h-[44px] min-w-[44px]", className)}>
                <Sun className="h-5 w-5" aria-hidden="true" />
                <span className="sr-only">Toggle theme</span>
            </Button>
        );
    }

    return (
        <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            className={cn("min-h-[44px] min-w-[44px]", className)}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
            {theme === 'light' ? (
                <Moon className="h-5 w-5" aria-hidden="true" />
            ) : (
                <Sun className="h-5 w-5" aria-hidden="true" />
            )}
            <span className="sr-only">Toggle theme</span>
        </Button>
    );
}

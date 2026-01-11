'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { Button } from './button';

/**
 * Theme toggle button for switching between light and dark modes.
 *
 * Persists preference to localStorage and respects system preference on first load.
 */
export function ThemeToggle() {
    const [theme, setTheme] = useState<'light' | 'dark'>('light');
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        // Check localStorage first, then system preference
        const stored = localStorage.getItem('theme');
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
    }, [theme, mounted]);

    const toggleTheme = () => {
        setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
    };

    // Prevent hydration mismatch
    if (!mounted) {
        return (
            <Button variant="ghost" size="sm" className="min-h-[44px] min-w-[44px]">
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
            className="min-h-[44px] min-w-[44px]"
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

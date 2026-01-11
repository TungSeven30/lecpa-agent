'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, MessageSquare, Briefcase, LogOut } from 'lucide-react';
import { cn } from '@/lib/utils';
import { signOut } from 'next-auth/react';
import { ThemeToggle } from './theme-toggle';

const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Chat', href: '/chat', icon: MessageSquare },
    { name: 'Cases', href: '/cases', icon: Briefcase },
];

/**
 * Sidebar navigation component.
 *
 * Uses semantic sidebar color tokens that support theming.
 */
export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="flex h-full w-64 flex-col bg-sidebar">
            {/* Logo */}
            <div className="flex h-16 items-center px-6">
                <span className="text-xl font-bold text-sidebar-foreground">
                    Le CPA Agent
                </span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 px-3 py-4">
                {navigation.map((item) => {
                    const isActive =
                        pathname === item.href ||
                        (item.href !== '/' && pathname.startsWith(item.href));

                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                'group flex min-h-[44px] items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                                isActive
                                    ? 'bg-sidebar-accent text-sidebar-foreground'
                                    : 'text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground'
                            )}
                        >
                            <item.icon
                                className={cn(
                                    'mr-3 h-5 w-5 flex-shrink-0',
                                    isActive
                                        ? 'text-sidebar-foreground'
                                        : 'text-sidebar-muted group-hover:text-sidebar-foreground'
                                )}
                                aria-hidden="true"
                            />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            {/* Bottom section */}
            <div className="border-t border-sidebar-border p-4 space-y-2">
                <div className="flex items-center justify-between px-3">
                    <span className="text-sm text-sidebar-muted">Theme</span>
                    <ThemeToggle className="text-sidebar-foreground hover:bg-sidebar-accent" />
                </div>
                <button
                    onClick={() => signOut()}
                    className="group flex min-h-[44px] w-full items-center rounded-md px-3 py-2 text-sm font-medium text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground"
                >
                    <LogOut
                        className="mr-3 h-5 w-5 text-sidebar-muted group-hover:text-sidebar-foreground"
                        aria-hidden="true"
                    />
                    Sign out
                </button>
            </div>
        </div>
    );
}

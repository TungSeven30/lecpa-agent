import { useEffect, useRef, useCallback, type RefObject } from 'react';

const FOCUSABLE_SELECTOR =
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Hook to trap focus within a container element.
 *
 * When active, prevents focus from leaving the container via Tab navigation.
 * Restores focus to the previously focused element when deactivated.
 *
 * Args:
 *     isActive: Whether the focus trap should be active
 *
 * Returns:
 *     Ref to attach to the container element that should trap focus
 */
export function useFocusTrap(isActive: boolean): RefObject<HTMLDivElement> {
    const containerRef = useRef<HTMLDivElement>(null);
    const previousFocusRef = useRef<HTMLElement | null>(null);

    const getFocusableElements = useCallback((): HTMLElement[] => {
        if (!containerRef.current) return [];
        return Array.from(
            containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        ).filter(
            (el) => !el.hasAttribute('disabled') && el.offsetParent !== null
        );
    }, []);

    useEffect(() => {
        if (!isActive) return;

        // Store the currently focused element
        previousFocusRef.current = document.activeElement as HTMLElement;

        // Focus the first focusable element
        const focusable = getFocusableElements();
        if (focusable.length > 0) {
            focusable[0].focus();
        }

        const handleKeyDown = (e: KeyboardEvent): void => {
            if (e.key !== 'Tab') return;

            const focusable = getFocusableElements();
            if (focusable.length === 0) return;

            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            // Shift+Tab from first element: go to last
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            }
            // Tab from last element: go to first
            else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        };

        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            // Restore focus to the previously focused element
            previousFocusRef.current?.focus();
        };
    }, [isActive, getFocusableElements]);

    return containerRef;
}

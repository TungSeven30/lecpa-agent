# Changelog

All notable changes to Le CPA Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Skeleton loading components (`Skeleton`, `CardSkeleton`, `ListItemSkeleton`, `StatCardSkeleton`) for better loading states
- `suppressHydrationWarning` on root HTML element to prevent theme toggle hydration mismatch warnings

### Changed
- **Color Scheme**: Updated to warm beige/cream palette for light mode
  - Background: `#FAF7F0` (warm cream)
  - Card surfaces: `#FFFDFA` (off-white with warm undertones)
  - Muted elements: `#F5F0E8` (light tan)
  - Accent color: `#B45309` (warm amber)
- **Dark Mode**: Updated to warm stone palette
  - Background: `#1C1917` (stone-900)
  - Card surfaces: `#292524` (stone-800)
  - Muted elements: `#44403C` (stone-700)
  - Accent color: `#F59E0B` (amber-500)

### Fixed
- **Dark Mode CSS Cascade**: Moved dark mode CSS variables outside `@layer base` to ensure proper specificity and reliable theme switching
- **Dashboard Layout**: Removed hard-coded `bg-gray-50` from main element that was overriding dark mode styles

### Technical Notes
- All UI components use semantic color tokens (`bg-card`, `bg-muted`, `border-border`) rather than hard-coded colors
- CSS variables use RGB triplets for Tailwind alpha value support (e.g., `rgb(var(--background) / <alpha-value>)`)
- Theme switching uses `darkMode: 'class'` strategy with `next-themes` provider

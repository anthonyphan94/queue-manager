/**
 * API Configuration Utilities
 * 
 * Centralized API base URL configuration.
 * Use relative URLs in production (served from same origin),
 * localhost in development.
 */

export const isDev = import.meta.env.DEV;

/**
 * Base URL for API calls.
 * - VITE_API_BASE overrides (useful when the dev SPA points at a remote backend)
 * - Otherwise: localhost:8080 in dev, same-origin ('') in production
 */
export const API_BASE: string =
    (import.meta.env.VITE_API_BASE as string | undefined) ??
    (isDev ? 'http://localhost:8080' : '');

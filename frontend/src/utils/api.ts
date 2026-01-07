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
 * - Development: http://localhost:8080
 * - Production: '' (relative URLs, same origin)
 */
export const API_BASE = isDev ? 'http://localhost:8080' : '';

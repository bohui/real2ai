/**
 * Route Discovery Utility for Real2AI
 * Advanced route extraction and sitemap generation from React Router configuration
 */

import { RouteObject } from 'react-router-dom';
import { SitemapUrl } from './seoUtils';

export interface DiscoveredRoute {
  path: string;
  type: 'homepage' | 'auth' | 'static' | 'content' | 'protected' | 'dynamic';
  isPublic: boolean;
  requiresAuth: boolean;
  isDynamic: boolean;
  component?: string;
  title?: string;
  description?: string;
  keywords?: string[];
}

/**
 * Route patterns and their classifications
 */
const ROUTE_PATTERNS = {
  homepage: /^\/$/,
  auth: /^\/auth/,
  api: /^\/api/,
  admin: /^\/admin/,
  app: /^\/app/,
  dynamic: /:[^/]+/,
  wildcard: /\*/
} as const;

/**
 * Extract all routes from React Router configuration
 */
export function extractAllRoutes(routes: RouteObject[], basePath = ''): DiscoveredRoute[] {
  const discoveredRoutes: DiscoveredRoute[] = [];
  
  function traverseRoutes(routeArray: RouteObject[], parentPath = '') {
    routeArray.forEach(route => {
      if (route.path) {
        const fullPath = joinPaths(parentPath, route.path);
        const routeInfo = analyzeRoute(fullPath, route);
        
        if (routeInfo) {
          discoveredRoutes.push(routeInfo);
        }
      }
      
      // Handle index routes
      if (route.index && parentPath) {
        const indexRouteInfo = analyzeRoute(parentPath, route);
        if (indexRouteInfo) {
          discoveredRoutes.push({
            ...indexRouteInfo,
            path: parentPath,
            type: 'static'
          });
        }
      }
      
      // Recursively process child routes
      if (route.children && route.children.length > 0) {
        const childBasePath = route.path ? joinPaths(parentPath, route.path) : parentPath;
        traverseRoutes(route.children, childBasePath);
      }
    });
  }
  
  traverseRoutes(routes, basePath);
  return discoveredRoutes;
}

/**
 * Analyze a route and determine its characteristics
 */
function analyzeRoute(path: string, route: RouteObject): DiscoveredRoute | null {
  // Skip empty paths
  if (!path) return null;
  
  // Normalize path
  const normalizedPath = normalizePath(path);
  
  // Determine route type
  const type = determineRouteType(normalizedPath);
  
  // Check if route is dynamic
  const isDynamic = ROUTE_PATTERNS.dynamic.test(normalizedPath) || 
                    ROUTE_PATTERNS.wildcard.test(normalizedPath);
  
  // Determine if route is public (should be included in sitemap)
  const isPublic = isPublicRoute(normalizedPath, type);
  
  // Determine if route requires authentication
  const requiresAuth = requiresAuthentication(normalizedPath, type);
  
  return {
    path: normalizedPath,
    type,
    isPublic,
    requiresAuth,
    isDynamic,
    component: extractComponentName(route),
    title: generateRouteTitle(normalizedPath),
    description: generateRouteDescription(normalizedPath),
    keywords: generateRouteKeywords(normalizedPath, type)
  };
}

/**
 * Determine route type based on path patterns
 */
function determineRouteType(path: string): DiscoveredRoute['type'] {
  if (ROUTE_PATTERNS.homepage.test(path)) return 'homepage';
  if (ROUTE_PATTERNS.auth.test(path)) return 'auth';
  if (ROUTE_PATTERNS.app.test(path)) return 'protected';
  if (ROUTE_PATTERNS.dynamic.test(path)) return 'dynamic';
  if (path.includes('/content') || path.includes('/blog') || path.includes('/articles')) return 'content';
  return 'static';
}

/**
 * Check if a route should be public (included in sitemap)
 */
function isPublicRoute(path: string, type: DiscoveredRoute['type']): boolean {
  // Always include homepage
  if (type === 'homepage') return true;
  
  // Include specific auth pages
  if (type === 'auth' && (path.includes('/login') || path.includes('/register'))) return true;
  
  // Include content pages
  if (type === 'content') return true;
  
  // Include specific static pages
  const publicStaticPages = ['/about', '/contact', '/privacy', '/terms', '/help', '/pricing'];
  if (type === 'static' && publicStaticPages.some(page => path.includes(page))) return true;
  
  // Exclude protected app routes
  if (type === 'protected') return false;
  
  // Exclude dynamic routes (they need specific content)
  if (type === 'dynamic') return false;
  
  // Exclude API routes
  if (path.startsWith('/api')) return false;
  
  return false;
}

/**
 * Check if a route requires authentication
 */
function requiresAuthentication(path: string, type: DiscoveredRoute['type']): boolean {
  if (type === 'protected') return true;
  if (path.startsWith('/app/')) return true;
  if (path.startsWith('/admin/')) return true;
  if (path.startsWith('/dashboard')) return true;
  return false;
}

/**
 * Extract component name from route object
 */
function extractComponentName(route: RouteObject): string | undefined {
  // This is a simplified version - in a real app you might want to extract
  // the actual component name from the element prop
  if (route.element) {
    return 'Component'; // Placeholder
  }
  return undefined;
}

/**
 * Generate SEO title for a route
 */
function generateRouteTitle(path: string): string {
  const titleMap: Record<string, string> = {
    '/': 'Real2AI - Australian Real Estate AI Assistant',
    '/auth/login': 'Login to Real2AI',
    '/auth/register': 'Register for Real2AI',
    '/about': 'About Real2AI - AI-Powered Real Estate Analysis',
    '/contact': 'Contact Real2AI Support',
    '/privacy': 'Privacy Policy - Real2AI',
    '/terms': 'Terms of Service - Real2AI'
  };
  
  return titleMap[path] || `${formatPathToTitle(path)} - Real2AI`;
}

/**
 * Generate SEO description for a route
 */
function generateRouteDescription(path: string): string {
  const descriptionMap: Record<string, string> = {
    '/': 'Advanced AI-powered real estate contract analysis and property intelligence for Australian professionals.',
    '/auth/login': 'Sign in to your Real2AI account to access powerful AI-driven real estate analysis tools.',
    '/auth/register': 'Create your Real2AI account and start analyzing real estate contracts with AI technology.',
    '/about': 'Learn about Real2AI\'s mission to revolutionize Australian real estate with AI-powered contract analysis.',
    '/contact': 'Get in touch with Real2AI support team for assistance with AI real estate analysis tools.',
    '/privacy': 'Real2AI privacy policy - How we protect your data and ensure secure real estate analysis.',
    '/terms': 'Real2AI terms of service - Guidelines for using our AI-powered real estate analysis platform.'
  };
  
  return descriptionMap[path] || `${formatPathToTitle(path)} page on Real2AI platform.`;
}

/**
 * Generate SEO keywords for a route
 */
function generateRouteKeywords(path: string, type: DiscoveredRoute['type']): string[] {
  const baseKeywords = ['Real2AI', 'real estate', 'Australia', 'AI analysis'];
  
  const typeKeywords: Record<DiscoveredRoute['type'], string[]> = {
    homepage: ['contract analysis', 'property intelligence', 'real estate AI'],
    auth: ['login', 'register', 'account', 'user authentication'],
    static: ['information', 'help', 'support'],
    content: ['articles', 'guides', 'resources'],
    protected: ['dashboard', 'analysis', 'reports'],
    dynamic: ['details', 'specific', 'individual']
  };
  
  const pathKeywords: Record<string, string[]> = {
    '/auth/login': ['sign in', 'user login', 'authentication'],
    '/auth/register': ['sign up', 'create account', 'registration'],
    '/about': ['company', 'mission', 'team', 'about us'],
    '/contact': ['support', 'help', 'contact us', 'customer service'],
    '/privacy': ['privacy policy', 'data protection', 'GDPR'],
    '/terms': ['terms of service', 'legal', 'conditions']
  };
  
  return [
    ...baseKeywords,
    ...typeKeywords[type],
    ...(pathKeywords[path] || [])
  ];
}

/**
 * Convert URL path to readable title
 */
function formatPathToTitle(path: string): string {
  return path
    .split('/')
    .filter(segment => segment && segment !== 'auth' && segment !== 'app')
    .map(segment => segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' '))
    .join(' ') || 'Home';
}

/**
 * Join path segments properly
 */
function joinPaths(...segments: string[]): string {
  return '/' + segments
    .filter(segment => segment && segment !== '/')
    .join('/')
    .split('/')
    .filter(Boolean)
    .join('/');
}

/**
 * Normalize path by removing trailing slashes and ensuring leading slash
 */
function normalizePath(path: string): string {
  if (!path || path === '/') return '/';
  
  // Ensure leading slash
  if (!path.startsWith('/')) {
    path = '/' + path;
  }
  
  // Remove trailing slash
  if (path.length > 1 && path.endsWith('/')) {
    path = path.slice(0, -1);
  }
  
  return path;
}

/**
 * Convert discovered routes to sitemap URLs
 */
export function routesToSitemapUrls(routes: DiscoveredRoute[], baseUrl: string): SitemapUrl[] {
  const currentDate = new Date().toISOString().split('T')[0];
  
  return routes
    .filter(route => route.isPublic && !route.isDynamic)
    .map(route => ({
      loc: `${baseUrl}${route.path}`,
      lastmod: currentDate,
      changefreq: getChangeFrequency(route.type),
      priority: getPriority(route.type, route.path)
    }));
}

/**
 * Get change frequency based on route type
 */
function getChangeFrequency(type: DiscoveredRoute['type']): SitemapUrl['changefreq'] {
  const frequencies: Record<DiscoveredRoute['type'], SitemapUrl['changefreq']> = {
    homepage: 'daily',
    auth: 'weekly',
    static: 'monthly',
    content: 'weekly',
    protected: 'daily',
    dynamic: 'weekly'
  };
  
  return frequencies[type];
}

/**
 * Get priority based on route type and specific path
 */
function getPriority(type: DiscoveredRoute['type'], path: string): string {
  // Specific path priorities
  if (path === '/') return '1.0';
  if (path === '/auth/login' || path === '/auth/register') return '0.8';
  if (path === '/about' || path === '/contact') return '0.7';
  
  // Type-based priorities
  const priorities: Record<DiscoveredRoute['type'], string> = {
    homepage: '1.0',
    auth: '0.8',
    static: '0.6',
    content: '0.7',
    protected: '0.5',
    dynamic: '0.6'
  };
  
  return priorities[type];
}

/**
 * Future-proofing: Extract routes from actual React Router config
 * This would be used in a more advanced setup where routes are dynamically discovered
 */
export function extractRoutesFromConfig(routerConfig: RouteObject[]): DiscoveredRoute[] {
  return extractAllRoutes(routerConfig);
}

/**
 * Export utilities for testing and development
 */
export const routeDiscoveryUtils = {
  analyzeRoute,
  determineRouteType,
  isPublicRoute,
  requiresAuthentication,
  formatPathToTitle,
  normalizePath,
  joinPaths
};
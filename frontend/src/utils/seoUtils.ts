/**
 * SEO Utility Functions for Real2AI
 * Handles XML sitemap generation, route discovery, and SEO metadata
 */

import { RouteObject } from 'react-router-dom';

export interface SitemapUrl {
  loc: string;
  lastmod: string;
  changefreq: 'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never';
  priority: string;
}

export interface SitemapData {
  urls: SitemapUrl[];
  baseUrl: string;
}

/**
 * Configuration for different route types
 */
const ROUTE_CONFIG = {
  homepage: {
    changefreq: 'daily' as const,
    priority: '1.0'
  },
  auth: {
    changefreq: 'weekly' as const,
    priority: '0.8'
  },
  static: {
    changefreq: 'monthly' as const,
    priority: '0.6'
  },
  content: {
    changefreq: 'weekly' as const,
    priority: '0.7'
  }
} as const;

/**
 * Define all public routes that should be included in the sitemap
 * These are routes that don't require authentication and should be indexed
 * 
 * NOTE: Currently the root route (/) requires authentication. In the future,
 * consider creating a public landing page for better SEO.
 */
export const PUBLIC_ROUTES = [
  {
    path: '/auth/login',
    type: 'auth' as keyof typeof ROUTE_CONFIG,
    description: 'Login to Real2AI'
  },
  {
    path: '/auth/register',
    type: 'auth' as keyof typeof ROUTE_CONFIG,
    description: 'Register for Real2AI'
  }
  // TODO: Add public landing page route when implemented
  // {
  //   path: '/',
  //   type: 'homepage' as keyof typeof ROUTE_CONFIG,
  //   description: 'Real2AI - Australian Real Estate AI Assistant'
  // }
] as const;

/**
 * Get the base URL for the application
 * Handles different environments (development, production)
 */
export function getBaseUrl(): string {
  // Production URL
  if (typeof window !== 'undefined') {
    const { protocol, host } = window.location;
    if (host.includes('real2.ai') || host.includes('real2ai')) {
      return `${protocol}//real2.ai`;
    }
  }
  
  // Environment variables
  if (import.meta.env.VITE_APP_URL) {
    return import.meta.env.VITE_APP_URL;
  }
  
  // Default production URL
  return 'https://real2.ai';
}

/**
 * Generate sitemap URL entries from route definitions
 */
export function generateSitemapUrls(routes: typeof PUBLIC_ROUTES, baseUrl: string): SitemapUrl[] {
  const currentDate = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
  
  return routes.map(route => {
    const config = ROUTE_CONFIG[route.type];
    
    return {
      loc: `${baseUrl}${route.path}`,
      lastmod: currentDate,
      changefreq: config.changefreq,
      priority: config.priority
    };
  });
}

/**
 * Generate XML sitemap content
 */
export function generateSitemapXml(sitemapData: SitemapData): string {
  const { urls } = sitemapData;
  
  const urlElements = urls.map(url => `
    <url>
      <loc>${url.loc}</loc>
      <lastmod>${url.lastmod}</lastmod>
      <changefreq>${url.changefreq}</changefreq>
      <priority>${url.priority}</priority>
    </url>
  `).join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urlElements}
</urlset>`;
}

/**
 * Generate sitemap index XML for multiple sitemaps
 * Future-proofing for content-based sitemaps
 */
export function generateSitemapIndexXml(sitemaps: { loc: string; lastmod: string }[]): string {
  const sitemapElements = sitemaps.map(sitemap => `
    <sitemap>
      <loc>${sitemap.loc}</loc>
      <lastmod>${sitemap.lastmod}</lastmod>
    </sitemap>
  `).join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapElements}
</sitemapindex>`;
}

/**
 * Extract routes from React Router configuration
 * This function can be extended to automatically discover routes
 */
export function extractRoutesFromConfig(routes: RouteObject[]): { path: string; type: keyof typeof ROUTE_CONFIG }[] {
  const extractedRoutes: { path: string; type: keyof typeof ROUTE_CONFIG }[] = [];
  
  function traverse(routeArray: RouteObject[], parentPath = '') {
    routeArray.forEach(route => {
      if (route.path && !route.path.includes(':')) { // Skip dynamic routes
        const fullPath = `${parentPath}/${route.path}`.replace(/\/+/g, '/');
        
        // Determine route type based on path
        let type: keyof typeof ROUTE_CONFIG = 'static';
        if (fullPath === '/') type = 'homepage';
        else if (fullPath.startsWith('/auth')) type = 'auth';
        else if (fullPath.includes('/content') || fullPath.includes('/blog')) type = 'content';
        
        extractedRoutes.push({ path: fullPath, type });
      }
      
      // Recursively process child routes
      if (route.children) {
        const currentPath = route.path ? `${parentPath}/${route.path}`.replace(/\/+/g, '/') : parentPath;
        traverse(route.children, currentPath);
      }
    });
  }
  
  traverse(routes);
  return extractedRoutes;
}

/**
 * Validate XML sitemap format
 */
export function validateSitemapXml(xml: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  // Basic XML structure validation
  if (!xml.includes('<?xml version="1.0" encoding="UTF-8"?>')) {
    errors.push('Missing XML declaration');
  }
  
  if (!xml.includes('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"')) {
    errors.push('Missing or incorrect urlset namespace');
  }
  
  // Count URL entries
  const urlMatches = xml.match(/<url>/g);
  const urlCount = urlMatches ? urlMatches.length : 0;
  
  if (urlCount === 0) {
    errors.push('No URL entries found');
  }
  
  if (urlCount > 50000) {
    errors.push('Too many URLs (limit: 50,000)');
  }
  
  // Validate required fields for each URL
  const urlBlocks = xml.match(/<url>[\s\S]*?<\/url>/g) || [];
  urlBlocks.forEach((urlBlock, index) => {
    if (!urlBlock.includes('<loc>')) {
      errors.push(`URL ${index + 1}: Missing <loc> element`);
    }
    
    if (!urlBlock.includes('<lastmod>')) {
      errors.push(`URL ${index + 1}: Missing <lastmod> element`);
    }
    
    // Validate date format
    const lastmodMatch = urlBlock.match(/<lastmod>(.*?)<\/lastmod>/);
    if (lastmodMatch && lastmodMatch[1]) {
      const datePattern = /^\d{4}-\d{2}-\d{2}$/;
      if (!datePattern.test(lastmodMatch[1])) {
        errors.push(`URL ${index + 1}: Invalid date format in <lastmod>`);
      }
    }
  });
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Generate robots.txt content
 */
export function generateRobotsTxt(baseUrl: string): string {
  return `# Real2AI Robots.txt
User-agent: *
Allow: /
Allow: /auth/
Allow: /auth/login
Allow: /auth/register

# Block private/sensitive areas
Disallow: /app/
Disallow: /api/
Disallow: /admin/
Disallow: /private/

# Sitemap location
Sitemap: ${baseUrl}/sitemap.xml

# Crawl delay (be respectful)
Crawl-delay: 1
`;
}

/**
 * Main function to generate complete sitemap data
 */
export function generateCompleteSitemap(): SitemapData {
  const baseUrl = getBaseUrl();
  const urls = generateSitemapUrls(PUBLIC_ROUTES, baseUrl);
  
  return {
    urls,
    baseUrl
  };
}

/**
 * Export functions for build-time generation
 */
export const buildTimeUtils = {
  generateSitemapXml,
  generateCompleteSitemap,
  validateSitemapXml,
  generateRobotsTxt,
  getBaseUrl
};
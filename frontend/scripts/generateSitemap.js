#!/usr/bin/env node

/**
 * Build-time XML Sitemap Generation Script for Real2AI
 * 
 * This script generates the XML sitemap and updates robots.txt during the build process.
 * It can be run standalone or integrated into the build pipeline.
 * 
 * Usage:
 *   node scripts/generateSitemap.js
 *   npm run build:sitemap
 */

import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// ES module compatibility
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const CONFIG = {
  baseUrl: process.env.VITE_APP_URL || 'https://real2.ai',
  outputDir: resolve(__dirname, '../public'),
  distDir: resolve(__dirname, '../dist'),
  sitemapFilename: 'sitemap.xml',
  robotsFilename: 'robots.txt',
  generateForBoth: true, // Generate for both public/ and dist/
};

// Route configuration matching the TypeScript version
const ROUTE_CONFIG = {
  homepage: {
    changefreq: 'daily',
    priority: '1.0'
  },
  auth: {
    changefreq: 'weekly',
    priority: '0.8'
  },
  static: {
    changefreq: 'monthly',
    priority: '0.6'
  },
  content: {
    changefreq: 'weekly',
    priority: '0.7'
  }
};

// Public routes that should be included in sitemap
// NOTE: Currently the root route (/) requires authentication. In the future,
// consider creating a public landing page for better SEO.
const PUBLIC_ROUTES = [
  {
    path: '/auth/login',
    type: 'auth',
    description: 'Login to Real2AI'
  },
  {
    path: '/auth/register',
    type: 'auth',
    description: 'Register for Real2AI'
  }
  // TODO: Add public landing page route when implemented
  // {
  //   path: '/',
  //   type: 'homepage',
  //   description: 'Real2AI - Australian Real Estate AI Assistant'
  // }
];

/**
 * Generate sitemap URL entries from route definitions
 */
function generateSitemapUrls(routes, baseUrl) {
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
function generateSitemapXml(urls) {
  const urlEntries = urls.map(url => `  <url>
    <loc>${url.loc}</loc>
    <lastmod>${url.lastmod}</lastmod>
    <changefreq>${url.changefreq}</changefreq>
    <priority>${url.priority}</priority>
  </url>`).join('\n');
  
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
${urlEntries}
</urlset>`;
}

/**
 * Generate robots.txt content
 */
function generateRobotsTxt(baseUrl) {
  return `# Real2AI Robots.txt
# Generated automatically - do not edit manually

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
Disallow: /_next/
Disallow: /assets/

# Block development files
Disallow: /*.json$
Disallow: /*.js.map$
Disallow: /*.css.map$

# Sitemap location
Sitemap: ${baseUrl}/sitemap.xml

# Crawl delay (be respectful to server resources)
Crawl-delay: 1

# Cache directive for search engines
Cache-delay: 86400
`;
}

/**
 * Validate XML sitemap format
 */
function validateSitemapXml(xml) {
  const errors = [];
  
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
  
  // Validate required fields
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
 * Ensure directory exists
 */
function ensureDirectoryExists(dirPath) {
  if (!existsSync(dirPath)) {
    mkdirSync(dirPath, { recursive: true });
    console.log(`📁 Created directory: ${dirPath}`);
  }
}

/**
 * Write file with error handling
 */
function writeFileWithErrorHandling(filepath, content, description) {
  try {
    writeFileSync(filepath, content, 'utf8');
    console.log(`✅ Generated ${description}: ${filepath}`);
    
    // Validate if it's an XML file
    if (filepath.endsWith('.xml')) {
      const validation = validateSitemapXml(content);
      if (!validation.valid) {
        console.warn(`⚠️  Validation warnings for ${description}:`);
        validation.errors.forEach(error => console.warn(`   - ${error}`));
      } else {
        console.log(`✅ Validation passed for ${description}`);
      }
    }
  } catch (error) {
    console.error(`❌ Failed to write ${description}:`, error.message);
    process.exit(1);
  }
}

/**
 * Main generation function
 */
function generateSitemap() {
  console.log('🚀 Starting XML Sitemap Generation for Real2AI...');
  console.log(`📍 Base URL: ${CONFIG.baseUrl}`);
  console.log(`📊 Routes to include: ${PUBLIC_ROUTES.length}`);
  
  // Generate sitemap data
  const urls = generateSitemapUrls(PUBLIC_ROUTES, CONFIG.baseUrl);
  const sitemapXml = generateSitemapXml(urls);
  const robotsTxt = generateRobotsTxt(CONFIG.baseUrl);
  
  // Ensure output directories exist
  ensureDirectoryExists(CONFIG.outputDir);
  if (CONFIG.generateForBoth) {
    ensureDirectoryExists(CONFIG.distDir);
  }
  
  // Generate files for public/ directory (development)
  const publicSitemapPath = resolve(CONFIG.outputDir, CONFIG.sitemapFilename);
  const publicRobotsPath = resolve(CONFIG.outputDir, CONFIG.robotsFilename);
  
  writeFileWithErrorHandling(publicSitemapPath, sitemapXml, 'XML Sitemap (public)');
  writeFileWithErrorHandling(publicRobotsPath, robotsTxt, 'robots.txt (public)');
  
  // Generate files for dist/ directory (production build)
  if (CONFIG.generateForBoth) {
    const distSitemapPath = resolve(CONFIG.distDir, CONFIG.sitemapFilename);
    const distRobotsPath = resolve(CONFIG.distDir, CONFIG.robotsFilename);
    
    writeFileWithErrorHandling(distSitemapPath, sitemapXml, 'XML Sitemap (dist)');
    writeFileWithErrorHandling(distRobotsPath, robotsTxt, 'robots.txt (dist)');
  }
  
  // Summary
  console.log('\\n📋 Generation Summary:');
  console.log(`   • ${urls.length} URLs included`);
  console.log(`   • XML Sitemap: ${sitemapXml.length} characters`);
  console.log(`   • Base URL: ${CONFIG.baseUrl}`);
  console.log(`   • Generated at: ${new Date().toISOString()}`);
  
  // List included URLs
  console.log('\\n🔗 Included URLs:');
  urls.forEach((url, index) => {
    console.log(`   ${index + 1}. ${url.loc} (priority: ${url.priority}, freq: ${url.changefreq})`);
  });
  
  console.log('\\n✅ Sitemap generation completed successfully!');
  console.log(`\\n💡 Next steps:`);
  console.log(`   • Test sitemap: ${CONFIG.baseUrl}/sitemap.xml`);
  console.log(`   • Submit to Google Search Console`);
  console.log(`   • Verify robots.txt: ${CONFIG.baseUrl}/robots.txt`);
}

/**
 * Handle command line execution
 */
if (import.meta.url === `file://${process.argv[1]}`) {
  // Handle environment variables
  if (process.argv.includes('--production')) {
    CONFIG.baseUrl = 'https://real2.ai';
  } else if (process.argv.includes('--development')) {
    CONFIG.baseUrl = 'http://localhost:3000';
  }
  
  // Handle verbose output
  if (process.argv.includes('--verbose')) {
    console.log('🔧 Configuration:', CONFIG);
    console.log('🛣️  Routes:', PUBLIC_ROUTES);
  }
  
  // Run generation
  try {
    generateSitemap();
  } catch (error) {
    console.error('❌ Failed to generate sitemap:', error);
    process.exit(1);
  }
}

// Export for programmatic usage
export {
  generateSitemap,
  generateSitemapXml,
  generateRobotsTxt,
  validateSitemapXml,
  CONFIG
};
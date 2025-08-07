/**
 * Enhanced Sitemap Generation for Real2AI
 * Generates comprehensive XML sitemaps with SEO optimization
 */

import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const PRODUCTION_URL = 'https://real2.ai';
const DEVELOPMENT_URL = 'http://localhost:5173';

// Route configurations
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

// Define all public routes (those that don't require authentication and should be indexed)
const PUBLIC_ROUTES = [
  {
    path: '/auth/login',
    type: 'auth',
    title: 'Login - Real2AI',
    description: 'Sign in to your Real2AI account',
    lastmod: new Date().toISOString().split('T')[0]
  },
  {
    path: '/auth/register',
    type: 'auth',
    title: 'Register - Real2AI',
    description: 'Create your Real2AI account',
    lastmod: new Date().toISOString().split('T')[0]
  }
  // Note: Homepage (/) currently requires authentication
  // Consider adding a public landing page for better SEO:
  // {
  //   path: '/',
  //   type: 'homepage',
  //   title: 'Real2AI - Australian Real Estate AI Assistant',
  //   description: 'Advanced AI-powered real estate contract analysis',
  //   lastmod: new Date().toISOString().split('T')[0]
  // }
];

// Generate sitemap URL entries
function generateSitemapUrls(routes, baseUrl) {
  return routes.map(route => {
    const config = ROUTE_CONFIG[route.type];
    
    return {
      loc: `${baseUrl}${route.path}`,
      lastmod: route.lastmod,
      changefreq: config.changefreq,
      priority: config.priority,
      title: route.title,
      description: route.description
    };
  });
}

// Generate XML sitemap
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

// Generate robots.txt
function generateRobotsTxt(baseUrl) {
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

# Block development and build files
Disallow: /src/
Disallow: /dist/
Disallow: /node_modules/
Disallow: /*.js$
Disallow: /*.css$
Disallow: /*.map$

# Sitemap location
Sitemap: ${baseUrl}/sitemap.xml

# Crawl delay (be respectful)
Crawl-delay: 1

# Allow common search engines
User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: Slurp
Allow: /
`;
}

// Generate comprehensive SEO meta information
function generateSEOReport(urls, baseUrl) {
  const report = {
    generated: new Date().toISOString(),
    baseUrl,
    totalUrls: urls.length,
    urls: urls.map(url => ({
      path: url.loc.replace(baseUrl, ''),
      title: url.title,
      description: url.description,
      priority: url.priority,
      changefreq: url.changefreq,
      lastmod: url.lastmod
    })),
    recommendations: []
  };

  // Add SEO recommendations
  if (urls.length === 0) {
    report.recommendations.push('No public URLs found. Consider adding a public landing page.');
  }

  if (!urls.some(url => url.loc === baseUrl || url.loc === `${baseUrl}/`)) {
    report.recommendations.push('Consider adding a public homepage for better SEO.');
  }

  if (urls.filter(url => url.priority === '1.0').length > 1) {
    report.recommendations.push('Multiple pages have priority 1.0. Consider prioritizing only the most important page.');
  }

  return report;
}

// Main execution
function main() {
  const args = process.argv.slice(2);
  const isProduction = args.includes('--production');
  const isVerbose = args.includes('--verbose');
  
  const baseUrl = isProduction ? PRODUCTION_URL : DEVELOPMENT_URL;
  const outputDir = join(__dirname, '..', '..', 'public');
  
  console.log(`\n🚀 Generating sitemap for Real2AI`);
  console.log(`Environment: ${isProduction ? 'Production' : 'Development'}`);
  console.log(`Base URL: ${baseUrl}`);
  console.log(`Output directory: ${outputDir}`);

  // Ensure output directory exists
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
    console.log(`✅ Created output directory: ${outputDir}`);
  }

  // Generate sitemap URLs
  const urls = generateSitemapUrls(PUBLIC_ROUTES, baseUrl);
  console.log(`📄 Generated ${urls.length} URL entries`);

  // Generate and write sitemap.xml
  const sitemapXml = generateSitemapXml(urls);
  const sitemapPath = join(outputDir, 'sitemap.xml');
  writeFileSync(sitemapPath, sitemapXml, 'utf8');
  console.log(`✅ Generated sitemap.xml`);

  // Generate and write robots.txt
  const robotsTxt = generateRobotsTxt(baseUrl);
  const robotsPath = join(outputDir, 'robots.txt');
  writeFileSync(robotsPath, robotsTxt, 'utf8');
  console.log(`✅ Generated robots.txt`);

  // Generate SEO report
  const seoReport = generateSEOReport(urls, baseUrl);
  const reportPath = join(outputDir, 'seo-report.json');
  writeFileSync(reportPath, JSON.stringify(seoReport, null, 2), 'utf8');
  console.log(`📊 Generated SEO report`);

  if (isVerbose) {
    console.log('\n📋 SEO Report Summary:');
    console.log(`• Total URLs: ${seoReport.totalUrls}`);
    console.log(`• Base URL: ${seoReport.baseUrl}`);
    console.log(`• Generated: ${seoReport.generated}`);
    
    if (seoReport.recommendations.length > 0) {
      console.log('\n💡 SEO Recommendations:');
      seoReport.recommendations.forEach((rec, i) => {
        console.log(`  ${i + 1}. ${rec}`);
      });
    }

    console.log('\n📑 URL Details:');
    seoReport.urls.forEach(url => {
      console.log(`  • ${url.path} (Priority: ${url.priority})`);
    });
  }

  // Validation
  if (urls.length === 0) {
    console.warn('⚠️  Warning: No public URLs found in sitemap');
    console.warn('   Consider adding a public landing page for better SEO');
  }

  console.log('\n🎉 Sitemap generation completed successfully!');
  console.log(`   View at: ${baseUrl}/sitemap.xml`);
  console.log(`   Robots: ${baseUrl}/robots.txt`);
}

// Run if called directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}

export { generateSitemapUrls, generateSitemapXml, generateRobotsTxt, generateSEOReport };
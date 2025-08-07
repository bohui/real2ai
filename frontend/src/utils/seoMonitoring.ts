/**
 * SEO Performance Monitoring and Analytics
 * Tracks SEO metrics and performance indicators with Core Web Vitals integration
 */

import { getWebVitalsMonitor } from './webVitals';

export interface CoreWebVitals {
  lcp?: number;
  fid?: number;
  cls?: number;
  fcp?: number;
  ttfb?: number;
}

export function getCurrentWebVitals(): CoreWebVitals {
  const monitor = getWebVitalsMonitor();
  const metrics = monitor.getMetrics();
  return {
    lcp: metrics.lcp?.value,
    fid: metrics.fid?.value,
    cls: metrics.cls?.value,
    fcp: metrics.fcp?.value,
    ttfb: metrics.ttfb?.value,
  };
}

export interface SEOMetrics {
  pageTitle: string;
  metaDescription: string;
  canonicalUrl: string;
  ogTags: Record<string, string>;
  twitterTags: Record<string, string>;
  structuredDataCount: number;
  errors: string[];
  warnings: string[];
  score: number;
}

export interface PerformanceMetrics {
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint?: number;
  largestContentfulPaint?: number;
  cumulativeLayoutShift?: number;
  firstInputDelay?: number;
  // Enhanced Web Vitals integration
  webVitals?: CoreWebVitals;
  performanceScore?: number;
  performanceGrade?: string;
}

/**
 * Analyze current page SEO
 */
export function analyzeSEO(): SEOMetrics {
  const errors: string[] = [];
  const warnings: string[] = [];
  let score = 100;

  // Get basic meta information
  const pageTitle = document.title;
  const metaDescription = document.querySelector('meta[name="description"]')?.getAttribute('content') || '';
  const canonicalUrl = document.querySelector('link[rel="canonical"]')?.getAttribute('href') || '';

  // Title validation
  if (!pageTitle) {
    errors.push('Missing page title');
    score -= 20;
  } else {
    if (pageTitle.length > 60) {
      warnings.push('Title too long (>60 characters)');
      score -= 5;
    }
    if (pageTitle.length < 30) {
      warnings.push('Title too short (<30 characters)');
      score -= 5;
    }
  }

  // Description validation
  if (!metaDescription) {
    errors.push('Missing meta description');
    score -= 15;
  } else {
    if (metaDescription.length > 160) {
      warnings.push('Meta description too long (>160 characters)');
      score -= 5;
    }
    if (metaDescription.length < 120) {
      warnings.push('Meta description too short (<120 characters)');
      score -= 3;
    }
  }

  // Canonical URL validation
  if (!canonicalUrl) {
    warnings.push('Missing canonical URL');
    score -= 10;
  }

  // Open Graph tags
  const ogTags: Record<string, string> = {};
  document.querySelectorAll('meta[property^="og:"]').forEach(meta => {
    const property = meta.getAttribute('property');
    const content = meta.getAttribute('content');
    if (property && content) {
      ogTags[property] = content;
    }
  });

  // Required OG tags validation
  const requiredOGTags = ['og:title', 'og:description', 'og:image', 'og:url'];
  requiredOGTags.forEach(tag => {
    if (!ogTags[tag]) {
      warnings.push(`Missing ${tag}`);
      score -= 5;
    }
  });

  // Twitter Card tags
  const twitterTags: Record<string, string> = {};
  document.querySelectorAll('meta[name^="twitter:"]').forEach(meta => {
    const name = meta.getAttribute('name');
    const content = meta.getAttribute('content');
    if (name && content) {
      twitterTags[name] = content;
    }
  });

  // Twitter Card validation
  if (!twitterTags['twitter:card']) {
    warnings.push('Missing Twitter card type');
    score -= 3;
  }

  // Structured data validation
  const structuredDataScripts = document.querySelectorAll('script[type="application/ld+json"]');
  const structuredDataCount = structuredDataScripts.length;

  if (structuredDataCount === 0) {
    warnings.push('No structured data found');
    score -= 10;
  }

  // Validate structured data JSON
  structuredDataScripts.forEach((script, index) => {
    try {
      JSON.parse(script.textContent || '');
    } catch (e) {
      errors.push(`Invalid JSON-LD in script ${index + 1}`);
      score -= 10;
    }
  });

  // Performance impact on SEO score
  const webVitals = getCurrentWebVitals();
  if (webVitals) {
    // Performance significantly impacts SEO rankings
    const performanceWeight = 0.3; // 30% weight for performance
    const performanceContribution = (webVitals.lcp ? 100 : 0) * performanceWeight;
    score = Math.round(score * 0.7 + performanceContribution);
    
    // Add performance-specific warnings
    if (!webVitals.lcp || webVitals.lcp > 2500) {
      warnings.push('Largest Contentful Paint is too slow (>2.5s)');
    }
    if (webVitals.cls && webVitals.cls > 0.1) {
      warnings.push('Cumulative Layout Shift exceeds recommended threshold');
    }
  }

  return {
    pageTitle,
    metaDescription,
    canonicalUrl,
    ogTags,
    twitterTags,
    structuredDataCount,
    errors,
    warnings,
    score: Math.max(0, score)
  };
}

/**
 * Monitor page performance metrics with Web Vitals integration
 */
export function analyzePerformance(): Promise<PerformanceMetrics> {
  return new Promise((resolve) => {
    const metrics: Partial<PerformanceMetrics> = {};

    // Basic timing metrics
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (navigation) {
      metrics.loadTime = navigation.loadEventEnd - navigation.loadEventStart;
      metrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
    }

    // Get comprehensive Web Vitals data
    const webVitals = getCurrentWebVitals();
    if (webVitals) {
      metrics.webVitals = webVitals;
      metrics.performanceScore = webVitals.lcp ? 100 : 0;
      metrics.performanceGrade = webVitals.lcp && webVitals.lcp < 2500 ? 'A' : 'C';
      metrics.firstContentfulPaint = webVitals.fcp;
      metrics.largestContentfulPaint = webVitals.lcp;
      metrics.cumulativeLayoutShift = webVitals.cls;
      metrics.firstInputDelay = webVitals.fid;
    } else {
      // Fallback to Performance Observer for legacy support
      if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'paint') {
              if (entry.name === 'first-contentful-paint') {
                metrics.firstContentfulPaint = entry.startTime;
              }
            } else if (entry.entryType === 'largest-contentful-paint') {
              metrics.largestContentfulPaint = entry.startTime;
            } else if (entry.entryType === 'layout-shift') {
              if (!metrics.cumulativeLayoutShift) {
                metrics.cumulativeLayoutShift = 0;
              }
              metrics.cumulativeLayoutShift += (entry as any).value;
            }
          }
        });

        try {
          observer.observe({ entryTypes: ['paint', 'largest-contentful-paint', 'layout-shift'] });
        } catch (e) {
          console.warn('Performance Observer not fully supported');
        }

        // Resolve after a short delay to collect metrics
        setTimeout(() => {
          resolve(metrics as PerformanceMetrics);
        }, 1000);
      } else {
        resolve(metrics as PerformanceMetrics);
      }
    }

    // If we have Web Vitals data, resolve immediately
    if (webVitals) {
      resolve(metrics as PerformanceMetrics);
    }
  });
}

/**
 * Generate comprehensive SEO report
 */
export async function generateSEOReport(): Promise<{
  seo: SEOMetrics;
  performance: PerformanceMetrics;
  timestamp: string;
  url: string;
}> {
  const seoMetrics = analyzeSEO();
  const performanceMetrics = await analyzePerformance();

  return {
    seo: seoMetrics,
    performance: performanceMetrics,
    timestamp: new Date().toISOString(),
    url: window.location.href
  };
}

/**
 * Track SEO changes over time
 */
class SEOTracker {
  private history: Array<{
    seo: SEOMetrics;
    performance: PerformanceMetrics;
    timestamp: string;
    url: string;
  }> = [];

  private storageKey = 'real2ai-seo-history';

  constructor() {
    this.loadHistory();
  }

  private loadHistory() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        this.history = JSON.parse(stored);
      }
    } catch (e) {
      console.warn('Failed to load SEO history from localStorage');
    }
  }

  private saveHistory() {
    try {
      // Keep only last 50 entries
      const recentHistory = this.history.slice(-50);
      localStorage.setItem(this.storageKey, JSON.stringify(recentHistory));
    } catch (e) {
      console.warn('Failed to save SEO history to localStorage');
    }
  }

  async track() {
    const report = await generateSEOReport();
    this.history.push(report);
    this.saveHistory();
    return report;
  }

  getHistory() {
    return [...this.history];
  }

  getLatest() {
    return this.history[this.history.length - 1];
  }

  clearHistory() {
    this.history = [];
    localStorage.removeItem(this.storageKey);
  }

  getScoreTrend(days: number = 7) {
    const cutoffTime = Date.now() - (days * 24 * 60 * 60 * 1000);
    const recentEntries = this.history.filter(entry => 
      new Date(entry.timestamp).getTime() > cutoffTime
    );

    return recentEntries.map(entry => ({
      timestamp: entry.timestamp,
      score: entry.seo.score,
      url: entry.url
    }));
  }
}

/**
 * Monitor SEO in real-time during development
 */
export function enableSEOMonitoring(options: {
  trackOnRouteChange?: boolean;
  alertOnScoreDrop?: number;
  logToConsole?: boolean;
} = {}) {
  const tracker = new SEOTracker();
  const { trackOnRouteChange = true, alertOnScoreDrop = 80, logToConsole = false } = options;

  // Track initial page load
  setTimeout(() => {
    tracker.track().then(report => {
      if (logToConsole) {
        console.group('🔍 SEO Analysis Report');
        console.log('Score:', report.seo.score);
        console.log('Errors:', report.seo.errors);
        console.log('Warnings:', report.seo.warnings);
        console.log('Performance:', report.performance);
        console.groupEnd();
      }

      if (report.seo.score < alertOnScoreDrop) {
        console.warn(`⚠️ SEO Score Alert: ${report.seo.score}/100`);
        console.warn('Issues:', [...report.seo.errors, ...report.seo.warnings]);
      }
    });
  }, 1000);

  // Track route changes
  if (trackOnRouteChange) {
    let currentUrl = window.location.href;
    
    const checkUrlChange = () => {
      if (window.location.href !== currentUrl) {
        currentUrl = window.location.href;
        setTimeout(() => {
          tracker.track();
        }, 500); // Allow time for page to render
      }
    };

    // Use MutationObserver to detect URL changes in SPAs
    const observer = new MutationObserver(checkUrlChange);
    observer.observe(document, { subtree: true, childList: true });

    // Also listen for popstate events
    window.addEventListener('popstate', checkUrlChange);
  }

  return tracker;
}

export default {
  analyzeSEO,
  analyzePerformance,
  generateSEOReport,
  SEOTracker,
  enableSEOMonitoring
};
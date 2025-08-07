/**
 * Dynamic Imports and Code Splitting Utilities
 * Optimizes bundle size with intelligent lazy loading and preloading
 */

import React, { ComponentType, LazyExoticComponent } from 'react';

export interface LoadingComponentProps {
  error?: Error | null;
  retry?: () => void;
  pastDelay?: boolean;
}

export interface DynamicImportOptions {
  loading?: ComponentType<LoadingComponentProps>;
  fallback?: ComponentType<{ error?: Error }>;
  preload?: boolean;
  timeout?: number;
  retryCount?: number;
}

export interface BundleAnalysis {
  totalSize: number;
  chunkSizes: Record<string, number>;
  recommendations: string[];
}

/**
 * Enhanced dynamic import with loading states and error handling
 */
export function createDynamicImport<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  options: DynamicImportOptions = {}
): LazyExoticComponent<T> {
  const {
    loading: LoadingComponent,
    fallback: FallbackComponent,
    preload = false,
    timeout = 10000,
    retryCount = 3
  } = options;

  // Preload the component if specified
  if (preload) {
    setTimeout(() => {
      importFn().catch(() => {
        // Silently handle preload errors
      });
    }, 100);
  }

  // Create enhanced import function with retry logic
  const enhancedImportFn = async (): Promise<{ default: T }> => {
    let lastError: Error;
    
    for (let attempt = 1; attempt <= retryCount; attempt++) {
      try {
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('Import timeout')), timeout);
        });
        
        const importPromise = importFn();
        
        return await Promise.race([importPromise, timeoutPromise]);
      } catch (error) {
        lastError = error as Error;
        
        if (attempt < retryCount) {
          // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
      }
    }
    
    throw lastError!;
  };

  return React.lazy(enhancedImportFn);
}

/**
 * Route-based code splitting utility
 */
export const RouteComponents = {
  // Auth routes
  LoginPage: createDynamicImport(
    () => import('@/pages/auth/LoginPage'),
    { preload: true } // Preload auth pages as they're likely needed
  ),
  RegisterPage: createDynamicImport(
    () => import('@/pages/auth/RegisterPage')
  ),

  // Main application pages
  DashboardPage: createDynamicImport(
    () => import('@/pages/DashboardPage'),
    { preload: true }
  ),
  AnalysisPage: createDynamicImport(
    () => import('@/pages/AnalysisPage')
  ),
  PropertyIntelligencePage: createDynamicImport(
    () => import('@/pages/PropertyIntelligencePage')
  ),
  MarketAnalysisPage: createDynamicImport(
    () => import('@/pages/MarketAnalysisPage')
  ),
  FinancialAnalysisPage: createDynamicImport(
    () => import('@/pages/FinancialAnalysisPage')
  ),
  ReportsPage: createDynamicImport(
    () => import('@/pages/ReportsPage')
  ),
  HistoryPage: createDynamicImport(
    () => import('@/pages/HistoryPage')
  ),
  SettingsPage: createDynamicImport(
    () => import('@/pages/SettingsPage')
  )
};

/**
 * Feature-based component splitting
 */
export const FeatureComponents = {
  // Document analysis components
  ContractAnalysisModal: createDynamicImport(
    () => import('@/components/contract/ContractAnalysisModal')
  ),
  ContractAnalysisProgress: createDynamicImport(
    () => import('@/components/contract/ContractAnalysisProgress')
  ),
  
  // Advanced analysis components
  RiskVisualization: createDynamicImport(
    () => import('@/components/analysis/RiskVisualization')
  ),
  ComplianceCheck: createDynamicImport(
    () => import('@/components/analysis/ComplianceCheck')
  ),

  // Performance monitoring
  PerformanceDashboard: createDynamicImport(
    () => import('@/components/performance/PerformanceDashboard')
  ),

  // SEO components
  SEODevTools: createDynamicImport(
    () => import('@/components/seo/SEODevTools')
  )
};

/**
 * Preload specific components based on user behavior
 */
export class ComponentPreloader {
  private preloadedComponents = new Set<string>();
  private preloadQueue: Array<() => Promise<any>> = [];
  private isProcessing = false;

  /**
   * Preload component based on route prediction
   */
  preloadByRoute(currentRoute: string) {
    const preloadMap: Record<string, string[]> = {
      '/dashboard': ['AnalysisPage', 'PropertyIntelligencePage'],
      '/auth/login': ['DashboardPage'],
      '/analysis': ['ContractAnalysisModal', 'RiskVisualization'],
      '/reports': ['PerformanceDashboard'],
      '/settings': ['SEODevTools']
    };

    const componentsToPreload = preloadMap[currentRoute] || [];
    
    componentsToPreload.forEach(componentName => {
      this.preloadComponent(componentName);
    });
  }

  /**
   * Preload component by name
   */
  preloadComponent(componentName: string) {
    if (this.preloadedComponents.has(componentName)) {
      return;
    }

    this.preloadedComponents.add(componentName);

    // Add to queue for processing
    const preloadFn = this.getPreloadFunction(componentName);
    if (preloadFn) {
      this.preloadQueue.push(preloadFn);
      this.processQueue();
    }
  }

  private getPreloadFunction(componentName: string): (() => Promise<any>) | null {
    const preloadMap: Record<string, () => Promise<any>> = {
      // Routes
      'LoginPage': () => import('@/pages/auth/LoginPage'),
      'RegisterPage': () => import('@/pages/auth/RegisterPage'),
      'DashboardPage': () => import('@/pages/DashboardPage'),
      'AnalysisPage': () => import('@/pages/AnalysisPage'),
      'PropertyIntelligencePage': () => import('@/pages/PropertyIntelligencePage'),
      'MarketAnalysisPage': () => import('@/pages/MarketAnalysisPage'),
      'FinancialAnalysisPage': () => import('@/pages/FinancialAnalysisPage'),
      'ReportsPage': () => import('@/pages/ReportsPage'),
      'HistoryPage': () => import('@/pages/HistoryPage'),
      'SettingsPage': () => import('@/pages/SettingsPage'),
      
      // Features
      'ContractAnalysisModal': () => import('@/components/contract/ContractAnalysisModal'),
      'ContractAnalysisProgress': () => import('@/components/contract/ContractAnalysisProgress'),
      'RiskVisualization': () => import('@/components/analysis/RiskVisualization'),
      'ComplianceCheck': () => import('@/components/analysis/ComplianceCheck'),
      'PerformanceDashboard': () => import('@/components/performance/PerformanceDashboard'),
      'SEODevTools': () => import('@/components/seo/SEODevTools')
    };

    return preloadMap[componentName] || null;
  }

  private async processQueue() {
    if (this.isProcessing || this.preloadQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    try {
      // Process queue with throttling to avoid overwhelming the browser
      while (this.preloadQueue.length > 0) {
        const preloadFn = this.preloadQueue.shift();
        if (preloadFn) {
          try {
            await preloadFn();
            // Small delay between preloads
            await new Promise(resolve => setTimeout(resolve, 100));
          } catch (error) {
            console.warn('Component preload failed:', error);
          }
        }
      }
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Preload components based on intersection observer
   */
  preloadOnHover(element: HTMLElement, componentName: string) {
    let hasPreloaded = false;

    const handleMouseEnter = () => {
      if (!hasPreloaded) {
        hasPreloaded = true;
        this.preloadComponent(componentName);
      }
    };

    element.addEventListener('mouseenter', handleMouseEnter, { once: true });

    // Cleanup function
    return () => {
      element.removeEventListener('mouseenter', handleMouseEnter);
    };
  }
}

/**
 * Bundle size analyzer
 */
export class BundleAnalyzer {
  private static instance: BundleAnalyzer;
  private chunkSizes: Record<string, number> = {};
  private recommendations: string[] = [];

  static getInstance(): BundleAnalyzer {
    if (!BundleAnalyzer.instance) {
      BundleAnalyzer.instance = new BundleAnalyzer();
    }
    return BundleAnalyzer.instance;
  }

  /**
   * Analyze current bundle size and performance
   */
  async analyzeBundleSize(): Promise<BundleAnalysis> {
    const analysis: BundleAnalysis = {
      totalSize: 0,
      chunkSizes: {},
      recommendations: []
    };

    try {
      // Get resource timing data
      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      resources.forEach(resource => {
        if (resource.name.includes('.js') || resource.name.includes('.css')) {
          const size = resource.transferSize || 0;
          const filename = resource.name.split('/').pop() || resource.name;
          
          analysis.chunkSizes[filename] = size;
          analysis.totalSize += size;
        }
      });

      // Generate recommendations
      analysis.recommendations = this.generateRecommendations(analysis);

      return analysis;
    } catch (error) {
      console.error('Bundle analysis failed:', error);
      return analysis;
    }
  }

  private generateRecommendations(analysis: BundleAnalysis): string[] {
    const recommendations: string[] = [];
    const sizeThresholds = {
      large: 500000, // 500KB
      medium: 200000, // 200KB
    };

    // Check total bundle size
    if (analysis.totalSize > 2000000) { // 2MB
      recommendations.push('Total bundle size exceeds 2MB. Consider implementing more aggressive code splitting.');
    }

    // Check individual chunk sizes
    Object.entries(analysis.chunkSizes).forEach(([filename, size]) => {
      if (size > sizeThresholds.large) {
        recommendations.push(`Large chunk detected: ${filename} (${Math.round(size / 1024)}KB). Consider splitting further.`);
      }
    });

    // Check for vendor chunks
    const vendorChunks = Object.keys(analysis.chunkSizes).filter(name => 
      name.includes('vendor') || name.includes('node_modules')
    );

    if (vendorChunks.length === 0) {
      recommendations.push('No vendor chunks detected. Consider extracting third-party libraries into separate chunks.');
    }

    // Performance recommendations
    if (analysis.totalSize > 1000000) { // 1MB
      recommendations.push('Consider implementing service worker caching for better repeat visit performance.');
    }

    return recommendations;
  }

  /**
   * Monitor runtime chunk loading performance
   */
  monitorChunkLoading() {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          const resource = entry as PerformanceResourceTiming;
          
          if (resource.name.includes('.js') && resource.name.includes('chunk')) {
            const loadTime = resource.responseEnd - resource.requestStart;
            
            if (loadTime > 3000) { // 3 seconds
              console.warn(`Slow chunk loading detected: ${resource.name} took ${loadTime}ms`);
            }
          }
        });
      });

      observer.observe({ entryTypes: ['resource'] });
    }
  }
}

/**
 * Smart preloading based on user behavior
 */
export function useSmartPreloading() {
  const preloader = new ComponentPreloader();

  React.useEffect(() => {
    // Monitor user interactions for preloading hints
    const handleMouseMove = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      const link = target.closest('a[href]') as HTMLAnchorElement;
      
      if (link) {
        const href = link.getAttribute('href');
        if (href?.startsWith('/')) {
          preloader.preloadByRoute(href);
        }
      }
    };

    // Throttled mouse move handler
    let throttleTimer: number;
    const throttledMouseMove = (event: MouseEvent) => {
      if (throttleTimer) return;
      
      throttleTimer = window.setTimeout(() => {
        handleMouseMove(event);
        throttleTimer = 0;
      }, 200);
    };

    document.addEventListener('mousemove', throttledMouseMove, { passive: true });

    return () => {
      document.removeEventListener('mousemove', throttledMouseMove);
      if (throttleTimer) {
        clearTimeout(throttleTimer);
      }
    };
  }, [preloader]);

  return preloader;
}

// Create global instances
export const componentPreloader = new ComponentPreloader();
export const bundleAnalyzer = BundleAnalyzer.getInstance();

// Initialize monitoring
if (typeof window !== 'undefined') {
  bundleAnalyzer.monitorChunkLoading();
}

export default {
  createDynamicImport,
  RouteComponents,
  FeatureComponents,
  ComponentPreloader,
  BundleAnalyzer,
  useSmartPreloading,
  componentPreloader,
  bundleAnalyzer
};
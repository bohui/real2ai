/**
 * Core Web Vitals Monitoring System
 * Tracks LCP, FID, CLS, FCP, TTFB for SEO performance optimization
 */

import React from 'react';

interface WebVitalMetric {
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  entries: PerformanceEntry[];
}

interface WebVitalsScore {
  lcp: WebVitalMetric | null;
  fid: WebVitalMetric | null;
  cls: WebVitalMetric | null;
  fcp: WebVitalMetric | null;
  ttfb: WebVitalMetric | null;
  overallScore: number;
  recommendations: string[];
}

class WebVitalsMonitor {
  private metrics: WebVitalsScore = {
    lcp: null,
    fid: null,
    cls: null,
    fcp: null,
    ttfb: null,
    overallScore: 0,
    recommendations: []
  };

  private observers: Map<string, PerformanceObserver> = new Map();
  private callbacks: Set<(metrics: WebVitalsScore) => void> = new Set();

  constructor() {
    this.initializeMonitoring();
  }

  /**
   * Initialize Core Web Vitals monitoring
   */
  private initializeMonitoring(): void {
    // Only run in browser environment
    if (typeof window === 'undefined') return;

    this.monitorLCP();
    this.monitorFID();
    this.monitorCLS();
    this.monitorFCP();
    this.monitorTTFB();
  }

  /**
   * Monitor Largest Contentful Paint (LCP)
   * Target: < 2.5 seconds
   */
  private monitorLCP(): void {
    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries() as PerformanceEntry[];
        const lastEntry = entries[entries.length - 1];
        
        if (lastEntry) {
          this.metrics.lcp = {
            name: 'LCP',
            value: lastEntry.startTime,
            rating: this.getRating('lcp', lastEntry.startTime),
            delta: lastEntry.startTime - (this.metrics.lcp?.value || 0),
            entries
          };
          this.updateOverallScore();
          this.notifyCallbacks();
        }
      });

      observer.observe({ entryTypes: ['largest-contentful-paint'] });
      this.observers.set('lcp', observer);
    } catch (error) {
      console.warn('LCP monitoring not supported:', error);
    }
  }

  /**
   * Monitor First Input Delay (FID)
   * Target: < 100ms
   */
  private monitorFID(): void {
    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries() as PerformanceEventTiming[];
        
        entries.forEach((entry) => {
          if (entry.processingStart && entry.startTime) {
            const fid = entry.processingStart - entry.startTime;
            
            this.metrics.fid = {
              name: 'FID',
              value: fid,
              rating: this.getRating('fid', fid),
              delta: fid - (this.metrics.fid?.value || 0),
              entries: [entry]
            };
            this.updateOverallScore();
            this.notifyCallbacks();
          }
        });
      });

      observer.observe({ entryTypes: ['first-input'] });
      this.observers.set('fid', observer);
    } catch (error) {
      console.warn('FID monitoring not supported:', error);
    }
  }

  /**
   * Monitor Cumulative Layout Shift (CLS)
   * Target: < 0.1
   */
  private monitorCLS(): void {
    try {
      let clsValue = 0;
      const entries: PerformanceEntry[] = [];

      const observer = new PerformanceObserver((list) => {
        const newEntries = list.getEntries() as PerformanceEntry[];
        
        newEntries.forEach((entry: any) => {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
            entries.push(entry);
          }
        });

        this.metrics.cls = {
          name: 'CLS',
          value: clsValue,
          rating: this.getRating('cls', clsValue),
          delta: clsValue - (this.metrics.cls?.value || 0),
          entries
        };
        this.updateOverallScore();
        this.notifyCallbacks();
      });

      observer.observe({ entryTypes: ['layout-shift'] });
      this.observers.set('cls', observer);
    } catch (error) {
      console.warn('CLS monitoring not supported:', error);
    }
  }

  /**
   * Monitor First Contentful Paint (FCP)
   * Target: < 1.8 seconds
   */
  private monitorFCP(): void {
    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint');
        
        if (fcpEntry) {
          this.metrics.fcp = {
            name: 'FCP',
            value: fcpEntry.startTime,
            rating: this.getRating('fcp', fcpEntry.startTime),
            delta: fcpEntry.startTime - (this.metrics.fcp?.value || 0),
            entries: [fcpEntry]
          };
          this.updateOverallScore();
          this.notifyCallbacks();
        }
      });

      observer.observe({ entryTypes: ['paint'] });
      this.observers.set('fcp', observer);
    } catch (error) {
      console.warn('FCP monitoring not supported:', error);
    }
  }

  /**
   * Monitor Time to First Byte (TTFB)
   * Target: < 600ms
   */
  private monitorTTFB(): void {
    try {
      // Get navigation timing
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      
      if (navigation) {
        const ttfb = navigation.responseStart - navigation.requestStart;
        
        this.metrics.ttfb = {
          name: 'TTFB',
          value: ttfb,
          rating: this.getRating('ttfb', ttfb),
          delta: ttfb - (this.metrics.ttfb?.value || 0),
          entries: [navigation]
        };
        this.updateOverallScore();
        this.notifyCallbacks();
      }
    } catch (error) {
      console.warn('TTFB monitoring not supported:', error);
    }
  }

  /**
   * Get rating for metric value
   */
  private getRating(metric: string, value: number): 'good' | 'needs-improvement' | 'poor' {
    const thresholds = {
      lcp: { good: 2500, poor: 4000 }, // ms
      fid: { good: 100, poor: 300 }, // ms
      cls: { good: 0.1, poor: 0.25 }, // unitless
      fcp: { good: 1800, poor: 3000 }, // ms
      ttfb: { good: 600, poor: 1500 } // ms
    };

    const threshold = thresholds[metric as keyof typeof thresholds];
    if (!threshold) return 'good';

    if (value <= threshold.good) return 'good';
    if (value <= threshold.poor) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Update overall performance score (0-100)
   */
  private updateOverallScore(): void {
    const metrics = [this.metrics.lcp, this.metrics.fid, this.metrics.cls, this.metrics.fcp, this.metrics.ttfb];
    const validMetrics = metrics.filter(m => m !== null) as WebVitalMetric[];
    
    if (validMetrics.length === 0) {
      this.metrics.overallScore = 0;
      return;
    }

    const scores = validMetrics.map(metric => {
      switch (metric.rating) {
        case 'good': return 100;
        case 'needs-improvement': return 65;
        case 'poor': return 25;
        default: return 0;
      }
    });

    this.metrics.overallScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    this.generateRecommendations();
  }

  /**
   * Generate performance recommendations
   */
  private generateRecommendations(): void {
    const recommendations: string[] = [];

    if (this.metrics.lcp?.rating !== 'good') {
      recommendations.push('Optimize LCP: Reduce server response times, eliminate render-blocking resources, optimize images');
    }

    if (this.metrics.fid?.rating !== 'good') {
      recommendations.push('Improve FID: Reduce JavaScript execution time, use web workers for heavy tasks, optimize third-party scripts');
    }

    if (this.metrics.cls?.rating !== 'good') {
      recommendations.push('Fix CLS: Specify image dimensions, avoid inserting content above existing content, use CSS transform animations');
    }

    if (this.metrics.fcp?.rating !== 'good') {
      recommendations.push('Optimize FCP: Eliminate render-blocking resources, minify CSS, optimize fonts loading');
    }

    if (this.metrics.ttfb?.rating !== 'good') {
      recommendations.push('Reduce TTFB: Optimize server performance, use CDN, enable browser caching, minimize redirects');
    }

    this.metrics.recommendations = recommendations;
  }

  /**
   * Subscribe to metrics updates
   */
  public subscribe(callback: (metrics: WebVitalsScore) => void): () => void {
    this.callbacks.add(callback);
    
    // Send current metrics immediately
    callback(this.metrics);
    
    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback);
    };
  }

  /**
   * Notify all subscribers
   */
  private notifyCallbacks(): void {
    this.callbacks.forEach(callback => callback(this.metrics));
  }

  /**
   * Get current metrics
   */
  public getMetrics(): WebVitalsScore {
    return { ...this.metrics };
  }

  /**
   * Get performance score for SEO integration
   */
  public getPerformanceScore(): number {
    return this.metrics.overallScore;
  }

  /**
   * Check if all Core Web Vitals are in good range
   */
  public areWebVitalsGood(): boolean {
    const coreMetrics = [this.metrics.lcp, this.metrics.fid, this.metrics.cls];
    return coreMetrics.every(metric => metric?.rating === 'good');
  }

  /**
   * Cleanup observers
   */
  public cleanup(): void {
    this.observers.forEach(observer => observer.disconnect());
    this.observers.clear();
    this.callbacks.clear();
  }
}

// Global instance
let webVitalsMonitor: WebVitalsMonitor | null = null;

/**
 * Get or create Web Vitals monitor instance
 */
export function getWebVitalsMonitor(): WebVitalsMonitor {
  if (!webVitalsMonitor) {
    webVitalsMonitor = new WebVitalsMonitor();
  }
  return webVitalsMonitor;
}

/**
 * Hook for React components to use Web Vitals
 */
export function useWebVitals() {
  const [metrics, setMetrics] = React.useState<WebVitalsScore>({
    lcp: null,
    fid: null,
    cls: null,
    fcp: null,
    ttfb: null,
    overallScore: 0,
    recommendations: []
  });

  React.useEffect(() => {
    const monitor = getWebVitalsMonitor();
    const unsubscribe = monitor.subscribe(setMetrics);
    
    return unsubscribe;
  }, []);

  return metrics;
}

// Export types for use in other components
export type { WebVitalMetric, WebVitalsScore };
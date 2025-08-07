/**
 * SEO Development Tools with Performance Integration
 * Provides real-time SEO analysis, Core Web Vitals monitoring, and optimization recommendations
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, AlertTriangle, CheckCircle, Info, X, RefreshCw, Zap, TrendingUp } from 'lucide-react';
import { analyzeSEO, analyzePerformance, SEOMetrics, PerformanceMetrics } from '@/utils/seoMonitoring';
import { getCurrentWebVitals, CoreWebVitals } from '@/utils/webVitals';
import { useSEOContext } from '@/contexts/SEOContext';

interface SEODevToolsProps {
  isOpen: boolean;
  onClose: () => void;
}

const SEODevTools: React.FC<SEODevToolsProps> = ({ isOpen, onClose }) => {
  const [seoData, setSeoData] = useState<SEOMetrics | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceMetrics | null>(null);
  const [webVitals, setWebVitals] = useState<CoreWebVitals | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'meta' | 'structured' | 'performance' | 'vitals'>('overview');
  
  const { currentSEO } = useSEOContext();

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const seo = analyzeSEO();
      const performance = await analyzePerformance();
      const vitals = getCurrentWebVitals();
      
      setSeoData(seo);
      setPerformanceData(performance);
      setWebVitals(vitals);
    } catch (error) {
      console.error('SEO analysis failed:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      runAnalysis();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getScoreGrade = (score: number) => {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                <Search className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">SEO Dev Tools</h2>
                <p className="text-sm text-gray-500">SEO analysis with Core Web Vitals monitoring</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={runAnalysis}
                disabled={isAnalyzing}
                className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <RefreshCw className={`w-5 h-5 ${isAnalyzing ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={onClose}
                className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex h-[60vh]">
            {/* Sidebar */}
            <div className="w-48 bg-gray-50 border-r">
              <nav className="p-4 space-y-1">
                {[
                  { id: 'overview', label: 'Overview', icon: Search },
                  { id: 'meta', label: 'Meta Tags', icon: Info },
                  { id: 'structured', label: 'Structured Data', icon: CheckCircle },
                  { id: 'performance', label: 'Performance', icon: TrendingUp },
                  { id: 'vitals', label: 'Web Vitals', icon: Zap }
                ].map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`w-full flex items-center gap-3 px-3 py-2 text-sm rounded-lg transition-colors ${
                        activeTab === tab.id
                          ? 'bg-primary-100 text-primary-700'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto">
              {activeTab === 'overview' && (
                <div className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* SEO Score */}
                    <div className="bg-white border rounded-lg p-4">
                      <h3 className="font-medium text-gray-900 mb-3">SEO Score</h3>
                      {seoData ? (
                        <div className="flex items-center gap-3">
                          <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg ${getScoreColor(seoData.score)}`}>
                            {getScoreGrade(seoData.score)}
                          </div>
                          <div>
                            <div className="text-2xl font-bold text-gray-900">{seoData.score}/100</div>
                            <div className="text-sm text-gray-500">Current page score</div>
                          </div>
                        </div>
                      ) : (
                        <div className="text-gray-500">Analyzing...</div>
                      )}
                    </div>

                    {/* Issues Summary */}
                    <div className="bg-white border rounded-lg p-4">
                      <h3 className="font-medium text-gray-900 mb-3">Issues</h3>
                      {seoData ? (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                            <span className="text-sm">{seoData.errors.length} Errors</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                            <span className="text-sm">{seoData.warnings.length} Warnings</span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-gray-500">Analyzing...</div>
                      )}
                    </div>
                  </div>

                  {/* Current SEO Context */}
                  <div className="mt-6 bg-gray-50 rounded-lg p-4">
                    <h3 className="font-medium text-gray-900 mb-3">Current SEO Context</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="font-medium text-gray-700">Title:</div>
                        <div className="text-gray-600 truncate">{currentSEO.title || 'Not set'}</div>
                      </div>
                      <div>
                        <div className="font-medium text-gray-700">Description:</div>
                        <div className="text-gray-600 truncate">{currentSEO.description || 'Not set'}</div>
                      </div>
                      <div>
                        <div className="font-medium text-gray-700">Canonical:</div>
                        <div className="text-gray-600 truncate">{currentSEO.canonical || 'Not set'}</div>
                      </div>
                      <div>
                        <div className="font-medium text-gray-700">Keywords:</div>
                        <div className="text-gray-600 truncate">
                          {currentSEO.keywords ? currentSEO.keywords.join(', ') : 'Not set'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Issues List */}
                  {seoData && (seoData.errors.length > 0 || seoData.warnings.length > 0) && (
                    <div className="mt-6">
                      <h3 className="font-medium text-gray-900 mb-3">Issues Details</h3>
                      <div className="space-y-2">
                        {seoData.errors.map((error, index) => (
                          <div key={index} className="flex items-start gap-2 p-3 bg-red-50 rounded-lg">
                            <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                            <span className="text-sm text-red-700">{error}</span>
                          </div>
                        ))}
                        {seoData.warnings.map((warning, index) => (
                          <div key={index} className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg">
                            <Info className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                            <span className="text-sm text-yellow-700">{warning}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'meta' && (
                <div className="p-6">
                  <h3 className="font-medium text-gray-900 mb-4">Meta Tags Analysis</h3>
                  {seoData ? (
                    <div className="space-y-4">
                      {/* Basic Meta */}
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Basic Meta Tags</h4>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="font-medium">Title:</span> {seoData.pageTitle}
                            <span className="text-gray-500 ml-2">({seoData.pageTitle.length} chars)</span>
                          </div>
                          <div>
                            <span className="font-medium">Description:</span> {seoData.metaDescription}
                            <span className="text-gray-500 ml-2">({seoData.metaDescription.length} chars)</span>
                          </div>
                          <div>
                            <span className="font-medium">Canonical:</span> {seoData.canonicalUrl || 'Not set'}
                          </div>
                        </div>
                      </div>

                      {/* Open Graph */}
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Open Graph Tags</h4>
                        <div className="space-y-2 text-sm">
                          {Object.entries(seoData.ogTags).map(([property, content]) => (
                            <div key={property}>
                              <span className="font-medium">{property}:</span> {content}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Twitter Card */}
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Twitter Card Tags</h4>
                        <div className="space-y-2 text-sm">
                          {Object.entries(seoData.twitterTags).map(([name, content]) => (
                            <div key={name}>
                              <span className="font-medium">{name}:</span> {content}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-500">Analyzing...</div>
                  )}
                </div>
              )}

              {activeTab === 'structured' && (
                <div className="p-6">
                  <h3 className="font-medium text-gray-900 mb-4">Structured Data</h3>
                  {seoData ? (
                    <div>
                      <div className="bg-gray-50 rounded-lg p-4 mb-4">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">Scripts Found: {seoData.structuredDataCount}</span>
                          <a
                            href="https://search.google.com/test/rich-results"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary-600 hover:text-primary-700"
                          >
                            Test with Google →
                          </a>
                        </div>
                      </div>
                      
                      {/* Show structured data scripts */}
                      <div className="space-y-4">
                        {Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map((script, index) => (
                          <div key={index} className="bg-gray-50 rounded-lg p-4">
                            <h4 className="font-medium text-gray-900 mb-2">Script {index + 1}</h4>
                            <pre className="text-xs bg-white p-3 rounded border overflow-x-auto">
                              {script.textContent}
                            </pre>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-500">Analyzing...</div>
                  )}
                </div>
              )}

              {activeTab === 'performance' && (
                <div className="p-6">
                  <h3 className="font-medium text-gray-900 mb-4">Performance Metrics</h3>
                  {performanceData ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Loading</h4>
                        <div className="space-y-2 text-sm">
                          <div>Load Time: {performanceData.loadTime?.toFixed(2)}ms</div>
                          <div>DOM Content Loaded: {performanceData.domContentLoaded?.toFixed(2)}ms</div>
                        </div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Web Vitals</h4>
                        <div className="space-y-2 text-sm">
                          <div>FCP: {performanceData.firstContentfulPaint?.toFixed(2)}ms</div>
                          <div>LCP: {performanceData.largestContentfulPaint?.toFixed(2)}ms</div>
                          <div>CLS: {performanceData.cumulativeLayoutShift?.toFixed(3)}</div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-500">Analyzing...</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default SEODevTools;
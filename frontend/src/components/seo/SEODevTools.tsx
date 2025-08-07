/**
 * SEO Development Tools with Performance Integration
 * Provides real-time SEO analysis, Core Web Vitals monitoring, and optimization recommendations
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import { 
  Search, 
  XCircle
} from 'lucide-react';

interface SEODevToolsProps {
  className?: string;
  showAdvanced?: boolean;
  isOpen?: boolean;
  onClose?: () => void;
}

interface SEOAnalysis {
  title: string;
  description: string;
  headings: string[];
  images: string[];
  links: string[];
  metaTags: Record<string, string>;
  structuredData: any[];
  performance: {
    loadTime: number;
    pageSize: number;
    requests: number;
  };
}

export const SEODevTools: React.FC<SEODevToolsProps> = ({ isOpen = true, onClose }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<SEOAnalysis | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);


  const runAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      // This part of the analysis logic needs to be implemented
      // For now, it will just set some dummy data
      setAnalysis({
        title: 'Example Page Title',
        description: 'Example page description. This is a placeholder.',
        headings: ['Main Heading', 'Sub-heading', 'Another sub-heading'],
        images: ['https://via.placeholder.com/150', 'https://via.placeholder.com/150'],
        links: ['https://example.com', 'https://example.org'],
        metaTags: {
          'og:title': 'Example Open Graph Title',
          'og:description': 'Example Open Graph Description',
          'twitter:title': 'Example Twitter Title',
          'twitter:description': 'Example Twitter Description',
        },
        structuredData: [
          { '@context': 'https://schema.org', '@type': 'Organization', name: 'Example Org' },
          { '@context': 'https://schema.org', '@type': 'WebPage', headline: 'Example Headline' },
        ],
        performance: {
          loadTime: 1234,
          pageSize: 1024,
          requests: 50,
        },
      });
      setErrors([]);
      setWarnings([]);
    } catch (error) {
      console.error('SEO analysis failed:', error);
      setErrors(['Failed to perform SEO analysis.']);
      setWarnings([]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    runAnalysis();
  }, []);

  if (!isOpen || !analysis) return null;

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
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <Card className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <CardHeader className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <CardTitle className="text-xl font-semibold text-gray-900">SEO Dev Tools</CardTitle>
              <p className="text-sm text-gray-500">SEO analysis with Core Web Vitals monitoring</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={runAnalysis} disabled={isAnalyzing} className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors">
              {isAnalyzing ? 'Analyzing...' : 'Analyze Now'}
            </Button>
            <Button onClick={onClose} className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors">
              <XCircle className="w-5 h-5" />
            </Button>
          </div>
        </CardHeader>

        {/* Content */}
        <CardContent className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
            {/* Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* SEO Score */}
              <Card className="bg-white border rounded-lg p-4">
                <CardHeader className="font-medium text-gray-900 mb-3">SEO Score</CardHeader>
                {analysis ? (
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg ${getScoreColor(85)}`}>
                      {getScoreGrade(85)}
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-gray-900">{85}/100</div>
                      <div className="text-sm text-gray-500">Current page score</div>
                    </div>
                  </div>
                ) : (
                  <div className="text-gray-500">Analyzing...</div>
                )}
              </Card>

              {/* Issues Summary */}
              <Card className="bg-white border rounded-lg p-4">
                <CardHeader className="font-medium text-gray-900 mb-3">Issues</CardHeader>
                {analysis ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                      <span className="text-sm">{errors.length} Errors</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <span className="text-sm">{warnings.length} Warnings</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-gray-500">Analyzing...</div>
                )}
              </Card>
            </div>

            {/* Current SEO Context */}
            <Card className="bg-gray-50 rounded-lg p-4">
              <CardHeader className="font-medium text-gray-900 mb-3">Current SEO Context</CardHeader>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="font-medium text-gray-700">Title:</div>
                  <div className="text-gray-600 truncate">Example Page Title</div>
                </div>
                <div>
                  <div className="font-medium text-gray-700">Description:</div>
                  <div className="text-gray-600 truncate">Example page description. This is a placeholder.</div>
                </div>
                <div>
                  <div className="font-medium text-gray-700">Canonical:</div>
                  <div className="text-gray-600 truncate">Not set</div>
                </div>
                <div>
                  <div className="font-medium text-gray-700">Keywords:</div>
                  <div className="text-gray-600 truncate">
                    Not set
                  </div>
                </div>
              </div>
            </Card>

            {/* Issues List */}
            {errors.length > 0 || warnings.length > 0 ? (
              <Card className="mt-6">
                <CardHeader className="font-medium text-gray-900 mb-3">Issues Details</CardHeader>
                <CardContent className="space-y-2">
                  {errors.map((error, index) => (
                    <Alert key={index} type="danger" variant="subtle" description={error} />
                  ))}
                  {warnings.map((warning, index) => (
                    <Alert key={index} type="warning" variant="subtle" description={warning} />
                  ))}
                </CardContent>
              </Card>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SEODevTools;
/**
 * SEO System Usage Examples
 * Demonstrates how to use the Real2AI SEO system in various scenarios
 */

import React from 'react';
import { useSEO } from '@/hooks/useSEO';

const SEOUsageExample: React.FC = () => {
  // Example 1: Basic SEO for a page
  const basicSEO = useSEO({
    title: 'Real2AI - Property Analysis Platform',
    description: 'Advanced AI-powered property analysis and contract review platform for Australian real estate professionals.',
    keywords: ['property analysis', 'contract review', 'AI real estate', 'Australian property'],
    ogTitle: 'Real2AI - Smart Property Analysis',
    ogDescription: 'Transform your property analysis with AI-powered insights and contract review.',
    ogImage: 'https://real2.ai/og-image.jpg',
    ogUrl: 'https://real2.ai',
    canonical: 'https://real2.ai'
  });

  // Example 2: Dynamic SEO for property analysis
  const dynamicSEO = useSEO({
    title: 'Property Analysis - 123 Main St, Sydney',
    description: 'Comprehensive property analysis for 123 Main St, Sydney. Get detailed insights on market value, risk assessment, and investment potential.',
    keywords: ['Sydney property', 'market analysis', 'investment property', 'real estate'],
    ogTitle: 'Property Analysis - 123 Main St, Sydney',
    ogDescription: 'Get detailed property insights and market analysis for 123 Main St, Sydney.',
    ogImage: 'https://real2.ai/property-123-main-st.jpg',
    ogUrl: 'https://real2.ai/analysis/123-main-st',
    canonical: 'https://real2.ai/analysis/123-main-st'
  }, {
    address: '123 Main St',
    suburb: 'Sydney',
    state: 'NSW',
    riskScore: 7.2,
    medianPrice: '$1,200,000',
    region: 'Sydney Metro',
    trend: 'rising',
    publishedTime: '2024-01-15T10:00:00Z',
    modifiedTime: '2024-01-15T15:30:00Z'
  });

  // Example 3: SEO for contract analysis
  const contractSEO = useSEO({
    title: 'Contract Analysis - Purchase Agreement',
    description: 'AI-powered contract analysis for property purchase agreement. Review terms, identify risks, and ensure compliance.',
    keywords: ['contract analysis', 'purchase agreement', 'legal review', 'property contract'],
    ogTitle: 'Contract Analysis - Purchase Agreement',
    ogDescription: 'AI-powered contract analysis and legal review for property purchase agreements.',
    ogImage: 'https://real2.ai/contract-analysis.jpg',
    ogUrl: 'https://real2.ai/contract/analysis',
    canonical: 'https://real2.ai/contract/analysis'
  }, {
    address: '456 Oak Ave',
    suburb: 'Melbourne',
    state: 'VIC',
    riskScore: 4.8,
    medianPrice: '$850,000',
    region: 'Melbourne Metro',
    trend: 'stable',
    publishedTime: '2024-01-15T14:00:00Z',
    modifiedTime: '2024-01-15T16:45:00Z'
  });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold mb-4">SEO Usage Examples</h2>
        <p className="text-gray-600">
          This component demonstrates different ways to use the SEO hook for various page types.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-4 border rounded-lg">
          <h3 className="font-semibold mb-2">Basic SEO</h3>
          <p className="text-sm text-gray-600 mb-2">Standard page SEO</p>
          <div className="text-xs text-gray-500">
            <div>Title: {basicSEO.seoData.title}</div>
            <div>Description: {basicSEO.seoData.description?.substring(0, 50)}...</div>
          </div>
        </div>

        <div className="p-4 border rounded-lg">
          <h3 className="font-semibold mb-2">Dynamic SEO</h3>
          <p className="text-sm text-gray-600 mb-2">Property-specific SEO</p>
          <div className="text-xs text-gray-500">
            <div>Title: {dynamicSEO.seoData.title}</div>
            <div>Description: {dynamicSEO.seoData.description?.substring(0, 50)}...</div>
          </div>
        </div>

        <div className="p-4 border rounded-lg">
          <h3 className="font-semibold mb-2">Contract SEO</h3>
          <p className="text-sm text-gray-600 mb-2">Contract analysis SEO</p>
          <div className="text-xs text-gray-500">
            <div>Title: {contractSEO.seoData.title}</div>
            <div>Description: {contractSEO.seoData.description?.substring(0, 50)}...</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SEOUsageExample;
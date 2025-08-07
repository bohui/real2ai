/**
 * SEO System Usage Examples
 * Demonstrates how to use the Real2AI SEO system in various scenarios
 */

import React from 'react';
import { usePageSEO } from '@/contexts/SEOContext';
import { withSEO, useSEOForPage } from '@/components/seo';
import { generateArticleData, generatePropertyData } from '@/utils/structuredData';

// Example 1: Using usePageSEO hook directly
const ExampleDashboardPage: React.FC = () => {
  usePageSEO({
    title: 'Dashboard - Real2AI',
    description: 'Your comprehensive real estate analysis dashboard with AI-powered insights.',
    keywords: ['dashboard', 'real estate analytics', 'AI insights'],
    canonical: '/app/dashboard',
    noIndex: true // Private page
  });

  return <div>Dashboard content...</div>;
};

// Example 2: Dynamic SEO based on data
const ExampleContractAnalysisPage: React.FC = () => {
  const [analysisData, setAnalysisData] = React.useState<any>(null);

  // Dynamic SEO updates when data changes
  const propertyAddress = analysisData?.property_address;
  const riskScore = analysisData?.risk_score;
  
  usePageSEO(
    {
      title: propertyAddress 
        ? `Contract Analysis - ${propertyAddress} - Real2AI`
        : 'Contract Analysis - Real2AI',
      description: propertyAddress && riskScore !== undefined
        ? `Comprehensive AI analysis of ${propertyAddress}. Risk level: ${riskScore >= 7 ? 'high' : 'low'}.`
        : 'AI-powered contract analysis for Australian real estate.',
      keywords: [
        'contract analysis',
        'real estate AI',
        'risk assessment',
        ...(propertyAddress ? [`${propertyAddress} contract`] : [])
      ],
      canonical: '/app/analysis',
      ogType: 'article',
      structuredData: propertyAddress ? [
        generateArticleData({
          title: `Contract Analysis - ${propertyAddress}`,
          description: `AI analysis results for ${propertyAddress}`,
          section: 'Contract Analysis',
          tags: ['real estate', 'contract analysis', 'AI']
        }),
        generatePropertyData({
          address: propertyAddress,
          propertyType: 'House'
        })
      ] : undefined
    },
    propertyAddress ? {
      address: propertyAddress,
      riskScore: riskScore,
      publishedTime: new Date().toISOString()
    } : undefined
  );

  return <div>Contract analysis content...</div>;
};

// Example 3: Using the hook-based approach for complex SEO
const ExamplePropertyListingPage: React.FC = () => {
  const [properties, setProperties] = React.useState([]);

  const { SEOComponent, updateSEO } = useSEOForPage({
    staticSEO: {
      title: 'Property Listings - Real2AI',
      description: 'Browse AI-analyzed property listings with comprehensive insights.',
      keywords: ['property listings', 'real estate', 'AI analysis'],
      canonical: '/app/properties'
    }
  });

  // Update SEO when properties change
  React.useEffect(() => {
    if (properties.length > 0) {
      updateSEO({
        title: `${properties.length} Properties - AI Analyzed - Real2AI`,
        description: `Browse ${properties.length} AI-analyzed properties with comprehensive risk assessments and market insights.`
      });
    }
  }, [properties, updateSEO]);

  return (
    <>
      {SEOComponent}
      <div>Property listings content...</div>
    </>
  );
};

// Example 4: Using Higher-Order Component (HOC) approach
const ExampleReportsPageBase: React.FC = () => {
  return <div>Reports content...</div>;
};

const ExampleReportsPage = withSEO(ExampleReportsPageBase, {
  staticSEO: {
    title: 'Reports - Real2AI',
    description: 'Generate comprehensive property analysis reports.',
    keywords: ['reports', 'property analysis', 'real estate documentation'],
    canonical: '/app/reports',
    noIndex: true
  }
});

// Example 5: SEO for a specific contract with breadcrumbs
const ExampleSpecificContractPage: React.FC<{ contractId: string }> = ({ contractId }) => {
  const [contractData, setContractData] = React.useState<any>(null);

  usePageSEO({
    title: contractData?.property_address 
      ? `Analysis - ${contractData.property_address} - Real2AI`
      : `Contract Analysis ${contractId} - Real2AI`,
    description: contractData?.property_address
      ? `Detailed AI analysis for ${contractData.property_address}. Risk assessment, compliance checks, and market insights.`
      : 'Comprehensive AI-powered contract analysis results.',
    canonical: `/app/analysis/${contractId}`,
    noIndex: true,
    breadcrumbs: [
      { name: 'Dashboard', url: '/app/dashboard' },
      { name: 'Analysis History', url: '/app/history' },
      { name: contractData?.property_address || `Contract ${contractId}`, url: `/app/analysis/${contractId}` }
    ],
    structuredData: contractData ? [
      generateArticleData({
        title: `Contract Analysis - ${contractData.property_address}`,
        description: `Professional AI analysis of real estate contract for ${contractData.property_address}`,
        publishedTime: contractData.created_at,
        modifiedTime: contractData.updated_at,
        section: 'Contract Analysis',
        tags: ['contract analysis', 'real estate', 'AI', contractData.property_address]
      })
    ] : undefined
  });

  return <div>Specific contract analysis content...</div>;
};

// Example 6: Public marketing page with full SEO
const ExampleLandingPage: React.FC = () => {
  usePageSEO({
    title: 'Real2AI - Transform Australian Real Estate with AI',
    description: 'Advanced AI-powered real estate contract analysis and property intelligence for Australian professionals. Analyze contracts, assess properties, and make informed decisions.',
    keywords: [
      'Real2AI',
      'real estate AI',
      'contract analysis',
      'property intelligence',
      'Australian real estate',
      'AI assistant',
      'property analysis',
      'real estate technology'
    ],
    canonical: '/',
    ogTitle: 'Real2AI - Transform Real Estate with AI',
    ogDescription: 'Advanced AI-powered tools for Australian real estate professionals.',
    ogImage: '/images/og-homepage.jpg',
    twitterCard: 'summary_large_image',
    structuredData: [
      {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'Real2AI',
        description: 'AI-powered real estate analysis platform',
        url: 'https://real2.ai'
      },
      {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'Real2AI',
        description: 'Advanced AI-powered real estate analysis',
        url: 'https://real2.ai',
        logo: 'https://real2.ai/images/logo.png'
      }
    ]
  });

  return <div>Landing page content...</div>;
};

export {
  ExampleDashboardPage,
  ExampleContractAnalysisPage,
  ExamplePropertyListingPage,
  ExampleReportsPage,
  ExampleSpecificContractPage,
  ExampleLandingPage
};
/**
 * SEO Configuration for Real2AI
 * Centralized SEO metadata and templates for all pages
 */

import { SEOData } from "@/components/seo/SEOHead";
import {
  generateArticleData,
  generateDefaultStructuredData,
  generatePropertyData,
} from "@/utils/structuredData";

// Base configuration
export const BASE_URL = "https://real2.ai";
export const SITE_NAME = "Real2AI";
export const SITE_DESCRIPTION =
  "Advanced AI-powered property analysis and contract review platform for Australian real estate professionals.";

// Default SEO configuration
export const DEFAULT_SEO: SEOData = {
  title: `${SITE_NAME} - Property Analysis Platform`,
  description: SITE_DESCRIPTION,
  keywords: [
    "property analysis",
    "contract review",
    "AI real estate",
    "Australian property",
  ],
  ogTitle: `${SITE_NAME} - Smart Property Analysis`,
  ogDescription:
    "Transform your property analysis with AI-powered insights and contract review.",
  ogImage: `${BASE_URL}/og-image.jpg`,
  ogUrl: BASE_URL,
  ogType: "website" as const,
  twitterCard: "summary_large_image" as const,
  canonical: BASE_URL,
  robots: "index, follow",
  author: SITE_NAME,
};

// Global structured data
export const ORGANIZATION_STRUCTURED_DATA = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Real2AI",
  description:
    "Advanced AI-powered real estate contract analysis and property intelligence for Australian professionals.",
  url: "https://real2.ai",
  logo: `${BASE_URL}/logo.svg`,
  foundingDate: "2024",
  founders: [{
    "@type": "Person",
    name: "Real2AI Team",
  }],
  address: {
    "@type": "PostalAddress",
    addressCountry: "AU",
    addressRegion: "NSW",
  },
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "customer service",
    email: "support@real2.ai",
  },
  sameAs: [
    "https://twitter.com/Real2AI",
    "https://linkedin.com/company/real2ai",
  ],
};

export const WEBSITE_STRUCTURED_DATA = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "Real2AI",
  description:
    "Advanced AI-powered real estate contract analysis and property intelligence for Australian professionals.",
  url: "https://real2.ai",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: "https://real2.ai/app/search?q={search_term_string}",
    },
    "query-input": "required name=search_term_string",
  },
  publisher: ORGANIZATION_STRUCTURED_DATA,
};

// SEO templates for dynamic content
export const SEO_TEMPLATES = {
  contractAnalysis: {
    title: (address?: string) =>
      address
        ? `Contract Analysis - ${address} - Real2AI`
        : "Contract Analysis - Real2AI",
    description: (address?: string, riskScore?: number) => {
      if (address && riskScore !== undefined) {
        const riskLevel = riskScore >= 7
          ? "high"
          : riskScore >= 4
          ? "moderate"
          : "low";
        return `Comprehensive AI analysis of ${address} property contract. Risk level: ${riskLevel}. Professional insights for Australian real estate transactions.`;
      }
      return "AI-powered contract analysis for Australian real estate. Get comprehensive risk assessment, compliance checks, and professional insights.";
    },
    keywords: (address?: string) => [
      "contract analysis",
      "real estate AI",
      "property contract",
      "risk assessment",
      "Australian property law",
      "legal analysis",
      ...(address
        ? [`${address} contract`, `${address} property analysis`]
        : []),
    ],
  },

  propertyIntelligence: {
    title: (suburb?: string, state?: string) => {
      if (suburb && state) {
        return `Property Intelligence - ${suburb}, ${state} - Real2AI`;
      }
      return "Property Intelligence - Real2AI";
    },
    description: (suburb?: string, state?: string, medianPrice?: string) => {
      if (suburb && state) {
        const priceInfo = medianPrice ? ` Median price: ${medianPrice}.` : "";
        return `Comprehensive property intelligence for ${suburb}, ${state}.${priceInfo} Market trends, price analysis, and investment insights powered by AI.`;
      }
      return "AI-powered property intelligence for Australian real estate. Market analysis, price trends, and investment insights for informed decisions.";
    },
    keywords: (suburb?: string, state?: string) => [
      "property intelligence",
      "real estate data",
      "market analysis",
      "property prices",
      "Australian property market",
      "investment analysis",
      ...(suburb ? [`${suburb} property`, `${suburb} real estate`] : []),
      ...(state ? [`${state} property market`] : []),
    ],
  },

  marketAnalysis: {
    title: (region?: string) =>
      region
        ? `Market Analysis - ${region} - Real2AI`
        : "Market Analysis - Australian Real Estate - Real2AI",
    description: (region?: string, trend?: string) => {
      const trendInfo = trend ? ` Current trend: ${trend}.` : "";
      const areaInfo = region ? ` for ${region}` : " across Australia";
      return `Comprehensive real estate market analysis${areaInfo}.${trendInfo} Expert insights, price trends, and market forecasts powered by AI.`;
    },
    keywords: (region?: string) => [
      "market analysis",
      "real estate trends",
      "property market",
      "Australian real estate",
      "market forecast",
      "investment insights",
      ...(region ? [`${region} market`, `${region} property trends`] : []),
    ],
  },

  financialAnalysis: {
    title: "Financial Analysis - Real Estate ROI - Real2AI",
    description:
      "Advanced financial analysis for real estate investments. Calculate ROI, cash flow, and investment potential with AI-powered insights for Australian properties.",
    keywords: [
      "financial analysis",
      "real estate ROI",
      "investment calculator",
      "property finance",
      "cash flow analysis",
      "Australian property investment",
    ],
  },
} as const;

// Page-specific SEO configurations
export const PAGE_SEO_CONFIG: Record<string, SEOData> = {
  // Public pages
  "/": {
    title: DEFAULT_SEO.title,
    description: DEFAULT_SEO.description,
    keywords: DEFAULT_SEO.keywords,
    ogTitle: DEFAULT_SEO.ogTitle,
    ogDescription: DEFAULT_SEO.ogDescription,
    canonical: DEFAULT_SEO.canonical,
    structuredData: generateDefaultStructuredData(),
  },

  // Auth pages
  "/auth/login": {
    title: "Login - Real2AI",
    description:
      "Sign in to your Real2AI account to access powerful AI-driven real estate analysis tools and property intelligence.",
    keywords: [
      "Real2AI login",
      "sign in",
      "real estate platform",
      "user authentication",
    ],
    canonical: "/auth/login",
    noIndex: true,
  },

  "/auth/register": {
    title: "Register - Real2AI",
    description:
      "Create your Real2AI account and start analyzing real estate contracts with AI technology. Join thousands of Australian property professionals.",
    keywords: [
      "Real2AI register",
      "sign up",
      "create account",
      "real estate AI",
    ],
    canonical: "/auth/register",
    ogTitle: "Join Real2AI - Start Your AI-Powered Real Estate Journey",
    ogDescription:
      "Create your account and access advanced real estate analysis tools trusted by Australian professionals.",
  },

  // App pages
  "/app/dashboard": {
    title: "Dashboard - Real2AI",
    description:
      "Your Real2AI dashboard - manage contract analyses, view property intelligence reports, and track your real estate portfolio performance.",
    keywords: [
      "Real2AI dashboard",
      "contract analysis dashboard",
      "property reports",
      "AI insights",
      "real estate management",
    ],
    canonical: "/app/dashboard",
    noIndex: true,
  },

  "/app/analysis": {
    title: "Contract Analysis - Real2AI",
    description:
      "Analyze real estate contracts with AI-powered insights, risk assessment, and compliance checks. Professional tools for Australian property law.",
    keywords: [
      "contract analysis",
      "AI analysis",
      "real estate contracts",
      "risk assessment",
      "compliance check",
      "Australian property law",
    ],
    canonical: "/app/analysis",
    noIndex: true,
  },

  "/app/history": {
    title: "Analysis History - Real2AI",
    description:
      "View your complete contract analysis history. Track insights, compare properties, and review past AI-powered assessments.",
    keywords: [
      "analysis history",
      "contract history",
      "property analysis records",
      "Real2AI reports",
    ],
    canonical: "/app/history",
    noIndex: true,
  },

  "/app/property-intelligence": {
    title: "Property Intelligence - Real2AI",
    description:
      "Comprehensive property intelligence powered by AI. Market analysis, price trends, suburb insights, and investment potential for Australian real estate.",
    keywords: [
      "property intelligence",
      "real estate data",
      "market analysis",
      "property prices",
      "Australian property market",
      "suburb analysis",
      "investment insights",
    ],
    canonical: "/app/property-intelligence",
    noIndex: true,
  },

  "/app/market-analysis": {
    title: "Market Analysis - Australian Real Estate - Real2AI",
    description:
      "Advanced market analysis for Australian real estate. Trends, forecasts, and insights powered by AI to guide your property investment decisions.",
    keywords: [
      "market analysis",
      "real estate trends",
      "property market",
      "Australian real estate",
      "market forecast",
      "investment insights",
      "property trends",
    ],
    canonical: "/app/market-analysis",
    noIndex: true,
  },

  "/app/financial-analysis": {
    title: "Financial Analysis - Real Estate ROI - Real2AI",
    description:
      "Calculate ROI, analyze cash flow, and assess investment potential with AI-powered financial tools designed for Australian property investors.",
    keywords: [
      "financial analysis",
      "real estate ROI",
      "investment calculator",
      "property finance",
      "cash flow analysis",
      "Australian property investment",
      "ROI calculator",
    ],
    canonical: "/app/financial-analysis",
    noIndex: true,
  },

  "/app/reports": {
    title: "Reports - Real2AI",
    description:
      "Generate comprehensive reports from your property analyses. Professional documentation for contracts, valuations, and investment assessments.",
    keywords: [
      "property reports",
      "analysis reports",
      "contract reports",
      "professional documentation",
      "Real2AI reports",
    ],
    canonical: "/app/reports",
    noIndex: true,
  },

  "/app/settings": {
    title: "Settings - Real2AI",
    description:
      "Manage your Real2AI account settings, preferences, and subscription. Customize your AI-powered real estate analysis experience.",
    keywords: [
      "account settings",
      "Real2AI settings",
      "user preferences",
      "subscription management",
    ],
    canonical: "/app/settings",
    noIndex: true,
  },
};

// Breadcrumb structured data generator
export const generateBreadcrumbStructuredData = (
  breadcrumbs: Array<{ name: string; url: string }>,
) => ({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: breadcrumbs.map((crumb, index) => ({
    "@type": "ListItem",
    position: index + 1,
    name: crumb.name,
    item: `${BASE_URL}${crumb.url}`,
  })),
});

// Article structured data generator (deprecated - use generateArticleData from structuredData.ts)
export const generateArticleStructuredData = (
  title: string,
  description: string,
  publishedTime?: string,
  modifiedTime?: string,
  author?: string,
  image?: string,
) => ({
  "@context": "https://schema.org",
  "@type": "Article",
  headline: title,
  description,
  image: image ? `${BASE_URL}${image}` : `${BASE_URL}/images/og-default.jpg`,
  datePublished: publishedTime || new Date().toISOString(),
  dateModified: modifiedTime || new Date().toISOString(),
  author: {
    "@type": "Person",
    name: author || SITE_NAME,
  },
  publisher: ORGANIZATION_STRUCTURED_DATA,
});

// Dynamic SEO data generator
export const generateSEOData = (
  path: string,
  dynamicData?: {
    title?: string;
    description?: string;
    keywords?: string[];
    address?: string;
    suburb?: string;
    state?: string;
    riskScore?: number;
    medianPrice?: string;
    region?: string;
    trend?: string;
    publishedTime?: string;
    modifiedTime?: string;
    breadcrumbs?: Array<{ name: string; url: string }>;
  },
): SEOData => {
  // Get base config for the path
  const baseConfig = PAGE_SEO_CONFIG[path] || {};

  // Generate dynamic content based on path and data
  let dynamicConfig: Partial<SEOData> = {};

  if (dynamicData) {
    const {
      title,
      description,
      keywords,
      address,
      suburb,
      state,
      riskScore,
      medianPrice,
      region,
      trend,
      publishedTime,
      modifiedTime,
      breadcrumbs,
    } = dynamicData;

    // Override with custom data if provided
    if (title) dynamicConfig.title = title;
    if (description) dynamicConfig.description = description;
    if (keywords) dynamicConfig.keywords = keywords;

    // Apply templates based on path
    if (path.includes("/analysis") && !dynamicConfig.title) {
      dynamicConfig.title = SEO_TEMPLATES.contractAnalysis.title(address);
      dynamicConfig.description = SEO_TEMPLATES.contractAnalysis.description(
        address,
        riskScore,
      );
      dynamicConfig.keywords = SEO_TEMPLATES.contractAnalysis.keywords(address);
    }

    if (path.includes("/property-intelligence") && !dynamicConfig.title) {
      dynamicConfig.title = SEO_TEMPLATES.propertyIntelligence.title(
        suburb,
        state,
      );
      dynamicConfig.description = SEO_TEMPLATES.propertyIntelligence
        .description(suburb, state, medianPrice);
      dynamicConfig.keywords = SEO_TEMPLATES.propertyIntelligence.keywords(
        suburb,
        state,
      );
    }

    if (path.includes("/market-analysis") && !dynamicConfig.title) {
      dynamicConfig.title = SEO_TEMPLATES.marketAnalysis.title(region);
      dynamicConfig.description = SEO_TEMPLATES.marketAnalysis.description(
        region,
        trend,
      );
      dynamicConfig.keywords = SEO_TEMPLATES.marketAnalysis.keywords(region);
    }

    // Add structured data
    const structuredData = [...(baseConfig.structuredData || [])];

    // Add breadcrumbs if provided
    if (breadcrumbs && breadcrumbs.length > 0) {
      structuredData.push(generateBreadcrumbStructuredData(breadcrumbs));
    }

    // Add article data for analysis pages
    if (path.includes("/analysis") && (address || dynamicConfig.title)) {
      structuredData.push(generateArticleData({
        title: dynamicConfig.title || baseConfig.title || DEFAULT_SEO.title ||
          "Contract Analysis",
        description: dynamicConfig.description || baseConfig.description ||
          DEFAULT_SEO.description || "AI-powered contract analysis",
        publishedTime,
        modifiedTime,
        section: "Contract Analysis",
        tags: dynamicConfig.keywords || baseConfig.keywords || [],
      }));
    }

    // Add property data for property intelligence pages
    if (path.includes("/property-intelligence") && address) {
      structuredData.push(generatePropertyData({
        address,
        propertyType: "House", // Default, could be enhanced with more data
      }));
    }

    dynamicConfig.structuredData = structuredData;

    // Add time-based meta tags
    if (publishedTime) dynamicConfig.publishedTime = publishedTime;
    if (modifiedTime) dynamicConfig.modifiedTime = modifiedTime;
  }

  // Merge base config with dynamic config
  return {
    ...baseConfig,
    ...dynamicConfig,
    ogUrl: baseConfig.canonical,
    ogTitle: dynamicConfig.title || baseConfig.ogTitle || baseConfig.title,
    ogDescription: dynamicConfig.description || baseConfig.ogDescription ||
      baseConfig.description,
  };
};

// Export SEO_CONFIG for backward compatibility
export const SEO_CONFIG = DEFAULT_SEO;

export default DEFAULT_SEO;

/**
 * Structured Data Generators for Real2AI SEO
 * Creates JSON-LD structured data for different content types
 */

import { SEO_CONFIG } from '@/config/seoConfig';

export interface BreadcrumbItem {
  name: string;
  url: string;
}

export interface ArticleData {
  title: string;
  description: string;
  publishedTime?: string;
  modifiedTime?: string;
  author?: string;
  image?: string;
  section?: string;
  tags?: string[];
}

export interface PropertyData {
  address: string;
  price?: number;
  bedrooms?: number;
  bathrooms?: number;
  parkingSpaces?: number;
  landArea?: number;
  buildingArea?: number;
  propertyType?: 'House' | 'Apartment' | 'Townhouse' | 'Unit' | 'Land';
  yearBuilt?: number;
}

export interface ReviewData {
  reviewBody: string;
  ratingValue: number;
  bestRating?: number;
  worstRating?: number;
  author: string;
  datePublished?: string;
}

/**
 * Generate Organization structured data
 */
export function generateOrganizationData() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Real2AI',
    description: 'Advanced AI-powered real estate contract analysis and property intelligence for Australian professionals.',
    url: 'https://real2.ai',
    logo: 'https://real2.ai/images/logo.png',
    foundingDate: '2024',
    founders: [{
      '@type': 'Person',
      name: 'Real2AI Team'
    }],
    address: {
      '@type': 'PostalAddress',
      addressCountry: 'AU',
      addressRegion: 'NSW'
    },
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'customer service',
      email: 'support@real2.ai',
      availableLanguage: 'en'
    },
    sameAs: [
      'https://twitter.com/Real2AI',
      'https://linkedin.com/company/real2ai'
    ],
    areaServed: {
      '@type': 'Country',
      name: 'Australia'
    },
    serviceType: [
      'Real Estate Analysis',
      'Contract Analysis',
      'Property Intelligence',
      'AI Consulting'
    ]
  };
}

/**
 * Generate WebSite structured data with search functionality
 */
export function generateWebsiteData() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Real2AI',
    description: 'Advanced AI-powered real estate contract analysis and property intelligence for Australian professionals.',
    url: 'https://real2.ai',
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: 'https://real2.ai/app/search?q={search_term_string}'
      },
      'query-input': 'required name=search_term_string'
    },
    publisher: generateOrganizationData()
  };
}

/**
 * Generate Breadcrumb structured data
 */
export function generateBreadcrumbData(breadcrumbs: BreadcrumbItem[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: breadcrumbs.map((crumb, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: crumb.name,
      item: `${SEO_CONFIG.baseUrl}${crumb.url}`
    }))
  };
}

/**
 * Generate Article structured data for analysis reports
 */
export function generateArticleData(data: ArticleData) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: data.title,
    description: data.description,
    image: data.image ? `${SEO_CONFIG.baseUrl}${data.image}` : `${SEO_CONFIG.baseUrl}${SEO_CONFIG.defaultImage}`,
    datePublished: data.publishedTime || new Date().toISOString(),
    dateModified: data.modifiedTime || new Date().toISOString(),
    author: {
      '@type': 'Person',
      name: data.author || SEO_CONFIG.author
    },
    publisher: generateOrganizationData(),
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': window.location.href
    },
    articleSection: data.section || 'Real Estate Analysis',
    keywords: data.tags?.join(', ') || 'real estate, AI analysis, property intelligence',
    inLanguage: 'en-AU'
  };
}

/**
 * Generate Property structured data for real estate listings
 */
export function generatePropertyData(data: PropertyData) {
  const baseData: any = {
    '@context': 'https://schema.org',
    '@type': 'RealEstateAgent',
    name: 'Real2AI Property Analysis',
    description: `AI-powered analysis for ${data.address}`,
    address: {
      '@type': 'PostalAddress',
      streetAddress: data.address,
      addressCountry: 'AU'
    }
  };

  // Add property details if available
  if (data.price) {
    baseData.priceRange = `$${data.price.toLocaleString()}`;
  }

  if (data.propertyType || data.bedrooms || data.bathrooms) {
    baseData.makesOffer = {
      '@type': 'Offer',
      itemOffered: {
        '@type': 'Accommodation',
        name: `${data.propertyType || 'Property'} at ${data.address}`,
        ...(data.bedrooms && { numberOfRooms: data.bedrooms }),
        ...(data.bathrooms && { numberOfBathroomsTotal: data.bathrooms }),
        ...(data.landArea && { floorSize: `${data.landArea} sqm` }),
        ...(data.yearBuilt && { yearBuilt: data.yearBuilt })
      }
    };
  }

  return baseData;
}

/**
 * Generate Service structured data for Real2AI services
 */
export function generateServiceData() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Service',
    name: 'AI-Powered Real Estate Analysis',
    description: 'Comprehensive AI-driven contract analysis and property intelligence for Australian real estate professionals.',
    provider: generateOrganizationData(),
    areaServed: {
      '@type': 'Country',
      name: 'Australia'
    },
    serviceType: 'Real Estate Analysis',
    audience: {
      '@type': 'Audience',
      name: 'Real Estate Professionals'
    },
    offers: {
      '@type': 'Offer',
      description: 'Professional real estate AI analysis services',
      areaServed: 'Australia'
    }
  };
}

/**
 * Generate FAQ structured data
 */
export function generateFAQData(faqs: { question: string; answer: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map(faq => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer
      }
    }))
  };
}

/**
 * Generate Review structured data
 */
export function generateReviewData(data: ReviewData) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Review',
    reviewBody: data.reviewBody,
    reviewRating: {
      '@type': 'Rating',
      ratingValue: data.ratingValue,
      bestRating: data.bestRating || 5,
      worstRating: data.worstRating || 1
    },
    author: {
      '@type': 'Person',
      name: data.author
    },
    datePublished: data.datePublished || new Date().toISOString(),
    itemReviewed: {
      '@type': 'Service',
      name: 'Real2AI Real Estate Analysis'
    }
  };
}

/**
 * Generate Software Application structured data
 */
export function generateSoftwareApplicationData() {
  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Real2AI',
    description: 'AI-powered real estate contract analysis and property intelligence platform',
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web Browser',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'AUD',
      description: 'Free tier available with premium options'
    },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: 4.8,
      reviewCount: 150,
      bestRating: 5,
      worstRating: 1
    },
    featureList: [
      'AI Contract Analysis',
      'Property Intelligence',
      'Market Analysis',
      'Risk Assessment',
      'Compliance Checking'
    ]
  };
}

/**
 * Combine multiple structured data items into an array
 */
export function combineStructuredData(...items: any[]): any[] {
  return items.filter(Boolean);
}

/**
 * Generate default structured data for all pages
 */
export function generateDefaultStructuredData(): any[] {
  return combineStructuredData(
    generateOrganizationData(),
    generateWebsiteData(),
    generateServiceData(),
    generateSoftwareApplicationData()
  );
}

export default {
  generateOrganizationData,
  generateWebsiteData,
  generateBreadcrumbData,
  generateArticleData,
  generatePropertyData,
  generateServiceData,
  generateFAQData,
  generateReviewData,
  generateSoftwareApplicationData,
  combineStructuredData,
  generateDefaultStructuredData
};
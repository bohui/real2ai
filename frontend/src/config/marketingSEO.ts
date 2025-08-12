/**
 * SEO Configuration for Real2.AI Marketing Landing Page
 * Optimized for Australian real estate AI market with 2024-2025 best practices
 */

export interface MarketingSEOConfig {
  page: {
    title: string;
    description: string;
    keywords: string[];
    canonical: string;
  };
  openGraph: {
    title: string;
    description: string;
    type: string;
    url: string;
    image: string;
    siteName: string;
    locale: string;
  };
  twitter: {
    card: string;
    title: string;
    description: string;
    image: string;
    site: string;
    creator: string;
  };
  structuredData: {
    organization: any;
    website: any;
    softwareApplication: any;
    breadcrumbList: any;
    faqPage: any;
    localBusiness: any;
  };
}

export const marketingSEOConfig: MarketingSEOConfig = {
  page: {
    title: "Real2.AI - AI-Powered Australian Real Estate Contract Analysis | Your AI Step Before The Deal",
    description: "Real2.AI provides intelligent Australian real estate contract analysis with 95%+ accuracy. State-specific compliance checking for NSW, VIC, QLD, SA, WA, TAS, NT, ACT. Instant risk assessment, comprehensive property intelligence. Start your free analysis today.",
    keywords: [
      // Primary keywords - high volume, high intent
      "Australian real estate AI",
      "contract analysis Australia", 
      "property risk assessment",
      "AI property assistant Australia",
      
      // State-specific long-tail keywords
      "NSW property contract analysis",
      "Victoria real estate AI",
      "Queensland contract review AI", 
      "contract analysis Sydney Melbourne Brisbane",
      
      // Feature-specific keywords
      "real estate compliance check",
      "Australian property laws AI",
      "contract AI analysis",
      "property purchase protection",
      "real estate due diligence AI",
      
      // Intent-based keywords
      "property contract review service",
      "Australian real estate assistant",
      "property investment analysis",
      "contract risk assessment tool",
      
      // Competitor and comparison keywords
      "best property analysis tool Australia",
      "AI contract review vs lawyer",
      "automated property compliance check",
      
      // Location-based keywords
      "real estate AI Sydney",
      "property analysis Melbourne",
      "contract review Brisbane",
      "Australian property tech"
    ],
    canonical: "https://real2.ai"
  },
  
  openGraph: {
    title: "Real2.AI - Your AI Step Before The Deal | Australian Real Estate AI",
    description: "Australia's most advanced AI real estate assistant. Analyze contracts, assess risks, and make confident property decisions with 95%+ accuracy. Covers all states: NSW, VIC, QLD, SA, WA, TAS, NT, ACT.",
    type: "website",
    url: "https://real2.ai",
    image: "https://real2.ai/og-image-marketing.jpg",
    siteName: "Real2.AI",
    locale: "en_AU"
  },
  
  twitter: {
    card: "summary_large_image",
    title: "Real2.AI - AI-Powered Australian Real Estate Contract Analysis",
    description: "Analyze contracts, assess risks, make confident property decisions. 95%+ accuracy across all Australian states. Start free analysis today.",
    image: "https://real2.ai/twitter-image-marketing.jpg",
    site: "@Real2AI",
    creator: "@Real2AI"
  },
  
  structuredData: {
    organization: {
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "Real2.AI",
      "description": "AI-powered Australian real estate contract analysis platform",
      "url": "https://real2.ai",
      "logo": "https://real2.ai/logo.png",
      "foundingDate": "2024",
      "founder": {
        "@type": "Person",
        "name": "Real2.AI Team"
      },
      "sameAs": [
        "https://linkedin.com/company/real2ai",
        "https://twitter.com/real2ai",
        "https://facebook.com/real2ai"
      ],
      "address": {
        "@type": "PostalAddress",
        "addressCountry": "AU",
        "addressRegion": "NSW"
      },
      "contactPoint": {
        "@type": "ContactPoint",
        "telephone": "+61-xxx-xxx-xxx",
        "contactType": "customer support",
        "availableLanguage": "English"
      }
    },
    
    website: {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "Real2.AI",
      "url": "https://real2.ai",
      "description": "AI-powered Australian real estate contract analysis",
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://real2.ai/search?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    },
    
    softwareApplication: {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "Real2.AI",
      "applicationCategory": "Real Estate AI Assistant",
      "operatingSystem": "Web Browser",
      "description": "AI-powered contract analysis and risk assessment for Australian real estate transactions",
      "url": "https://real2.ai",
      "screenshot": "https://real2.ai/screenshot.jpg",
      "softwareVersion": "1.0",
      "datePublished": "2024-01-01",
      "dateModified": "2024-12-01",
      "author": {
        "@type": "Organization",
        "name": "Real2.AI"
      },
      "offers": {
        "@type": "Offer",
        "price": "49.00",
        "priceCurrency": "AUD",
        "priceValidUntil": "2025-12-31",
        "availability": "https://schema.org/InStock",
        "category": "Real Estate Software"
      },
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.8",
        "reviewCount": "247",
        "bestRating": "5",
        "worstRating": "1"
      },
      "featureList": [
        "AI Contract Analysis",
        "Risk Assessment", 
        "Compliance Checking",
        "OCR Document Processing",
        "Real-time Analysis",
        "Australian State Coverage",
        "Market Intelligence Integration"
      ]
    },
    
    breadcrumbList: {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "name": "Home",
          "item": "https://real2.ai"
        },
        {
          "@type": "ListItem", 
          "position": 2,
          "name": "AI Contract Analysis",
          "item": "https://real2.ai/analysis"
        },
        {
          "@type": "ListItem",
          "position": 3,
          "name": "Australian Real Estate",
          "item": "https://real2.ai/australian-real-estate"
        }
      ]
    },
    
    faqPage: {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "How accurate is Real2.AI's contract analysis?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Real2.AI achieves 95%+ accuracy in identifying contract risks, compliance issues, and unfavorable terms through our advanced AI models including GPT-4 and Gemini 2.5 Pro, specifically trained on Australian property law."
          }
        },
        {
          "@type": "Question",
          "name": "Which Australian states are supported?",
          "acceptedAnswer": {
            "@type": "Answer", 
            "text": "Real2.AI supports all Australian states and territories: NSW, VIC, QLD, SA, WA, TAS, NT, and ACT. Our AI is trained on state-specific property laws and regulations."
          }
        },
        {
          "@type": "Question",
          "name": "How long does contract analysis take?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Most contracts are analyzed within 2-5 minutes. Complex documents may take up to 10 minutes. You'll receive real-time progress updates throughout the process."
          }
        },
        {
          "@type": "Question",
          "name": "Is my contract data secure?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes, we use enterprise-grade security with end-to-end encryption. Your documents are processed securely and automatically deleted after analysis unless you choose to save them."
          }
        },
        {
          "@type": "Question",
          "name": "Can Real2.AI replace my conveyancer or lawyer?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Real2.AI is designed to complement, not replace, professional legal advice. Our AI analysis helps you identify potential issues early and have more informed discussions with your legal team."
          }
        }
      ]
    },
    
    localBusiness: {
      "@context": "https://schema.org",
      "@type": "LocalBusiness",
      "name": "Real2.AI",
      "description": "AI-powered Australian real estate contract analysis service",
      "url": "https://real2.ai",
      "telephone": "+61-xxx-xxx-xxx",
      "email": "hello@real2.ai",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "Level 1, 100 George Street",
        "addressLocality": "Sydney",
        "addressRegion": "NSW",
        "postalCode": "2000",
        "addressCountry": "AU"
      },
      "geo": {
        "@type": "GeoCoordinates",
        "latitude": "-33.8688",
        "longitude": "151.2093"
      },
      "areaServed": [
        {
          "@type": "State",
          "name": "New South Wales"
        },
        {
          "@type": "State", 
          "name": "Victoria"
        },
        {
          "@type": "State",
          "name": "Queensland"
        },
        {
          "@type": "State",
          "name": "South Australia"
        },
        {
          "@type": "State",
          "name": "Western Australia"
        },
        {
          "@type": "State",
          "name": "Tasmania"
        },
        {
          "@type": "State",
          "name": "Northern Territory"
        },
        {
          "@type": "State",
          "name": "Australian Capital Territory"
        }
      ],
      "serviceType": "AI Real Estate Assistant",
      "priceRange": "$49-$199",
      "openingHours": "Mo-Fr 09:00-17:00",
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.8",
        "reviewCount": "247"
      }
    }
  }
};

/**
 * Content optimization rules for Australian market
 */
export const contentOptimization = {
  // Primary value propositions for different user segments
  valueProps: {
    firstTimeBuyers: {
      headline: "Avoid Costly Mistakes on Your First Property Purchase",
      subheadline: "AI-powered contract analysis identifies hidden risks before you sign",
      cta: "Protect Your Investment"
    },
    
    investors: {
      headline: "Maximize ROI with Intelligent Property Analysis", 
      subheadline: "Professional-grade due diligence in minutes, not weeks",
      cta: "Analyze Investment"
    },
    
    buyersAgents: {
      headline: "Enhance Client Service with AI-Powered Insights",
      subheadline: "Provide instant contract analysis and build client trust",
      cta: "Upgrade Your Service"
    }
  },
  
  // Australian-specific content elements
  localizations: {
    currency: "AUD",
    states: ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"],
    legalTerms: [
      "cooling-off period",
      "stamp duty",
      "conveyancer",
      "settlement period",
      "building inspection",
      "pest inspection",
      "contract of sale",
      "deposit bond"
    ],
    propertyTypes: [
      "house and land package",
      "off-the-plan apartment",
      "established property",
      "investment property",
      "commercial property"
    ]
  },
  
  // SEO content templates for different page sections
  sectionTemplates: {
    hero: {
      h1Pattern: "[Emotional Hook] + [AI/Technology] + [Australian Context] + [Outcome]",
      examples: [
        "Your AI Step Before the Deal - Australia's Smartest Property Assistant",
        "Eliminate Property Purchase Risks with AI-Powered Contract Analysis", 
        "Make Confident Australian Property Decisions with 95% AI Accuracy"
      ]
    },
    
    benefits: {
      pattern: "[Specific Benefit] + [Technology] + [Australian Context] + [Metric/Proof]",
      examples: [
        "Instant Risk Detection: AI analyzes Australian contracts with 95%+ accuracy",
        "State Compliance: Covers all 8 Australian states and territories",
        "Speed Advantage: 3-minute analysis vs 2-week legal review"
      ]
    }
  }
};

/**
 * Technical SEO requirements implementation
 */
export const technicalSEO = {
  coreWebVitals: {
    lcp: {
      target: 2.5, // seconds
      optimizations: [
        "Hero image optimization",
        "Font loading strategy", 
        "Critical CSS inlining",
        "Server-side rendering"
      ]
    },
    
    inp: {
      target: 200, // milliseconds
      optimizations: [
        "JavaScript bundle splitting",
        "Event handler optimization",
        "Main thread work reduction"
      ]
    },
    
    cls: {
      target: 0.1,
      optimizations: [
        "Image dimension attributes",
        "Font loading strategy",
        "Dynamic content reservations"
      ]
    }
  },
  
  structuredDataPriority: [
    "Organization",
    "WebSite", 
    "SoftwareApplication",
    "FAQPage",
    "LocalBusiness",
    "BreadcrumbList"
  ],
  
  metaTagRequirements: {
    title: {
      minLength: 30,
      maxLength: 60,
      pattern: "Primary Keyword + Value Prop + Brand + Location"
    },
    description: {
      minLength: 120,
      maxLength: 160, 
      pattern: "Value Prop + Features + Location + CTA"
    }
  }
};
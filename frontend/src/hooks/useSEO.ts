/**
 * Enhanced SEO Hook for Real2AI
 * Provides dynamic SEO management with structured data and advanced features
 */

import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { generateSEOData } from "@/config/seoConfig";
import type { SEOData } from "@/components/seo/SEOHead";

export type { SEOData } from "@/components/seo/SEOHead";

export interface DynamicSEOData {
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
}

// SEO configurations now managed in seoConfig.ts

/**
 * Enhanced custom hook for SEO management
 */
export function useSEO(
  customSEO?: Partial<SEOData>,
  dynamicData?: DynamicSEOData,
) {
  const location = useLocation();
  const [currentSEO, setCurrentSEO] = useState<SEOData>({});
  const [isLoading, setIsLoading] = useState(false);

  // Generate SEO data based on current path and dynamic content
  const generateCurrentSEO = useCallback(() => {
    const generatedSEO = generateSEOData(location.pathname, dynamicData);

    // Merge with custom SEO overrides
    const finalSEO: SEOData = {
      ...generatedSEO,
      ...customSEO,
    };

    return finalSEO;
  }, [location.pathname, customSEO, dynamicData]);

  // Update SEO data
  const updateSEO = useCallback((newSEO: Partial<SEOData> | DynamicSEOData) => {
    setIsLoading(true);

    // If it contains dynamic data properties, treat as dynamic data
    const isDynamicData = "address" in newSEO || "suburb" in newSEO ||
      "riskScore" in newSEO;

    if (isDynamicData) {
      const generatedSEO = generateSEOData(
        location.pathname,
        newSEO as DynamicSEOData,
      );
      setCurrentSEO((prevSEO) => ({ ...prevSEO, ...generatedSEO }));
    } else {
      setCurrentSEO((prevSEO) => ({ ...prevSEO, ...newSEO }));
    }

    setIsLoading(false);
  }, [location.pathname]);

  // Initialize SEO data on mount or path change
  useEffect(() => {
    setIsLoading(true);
    const newSEO = generateCurrentSEO();
    setCurrentSEO(newSEO);
    setIsLoading(false);
  }, [generateCurrentSEO]);

  // Legacy DOM manipulation (kept for compatibility)
  useEffect(() => {
    if (isLoading || !currentSEO.title) return;

    // Update document title
    const finalTitle = currentSEO.title.includes("Real2AI")
      ? currentSEO.title
      : `${currentSEO.title} - Real2AI`;

    document.title = finalTitle;

    // Update basic meta tags
    updateMetaTag("description", currentSEO.description);
    updateMetaTag(
      "keywords",
      Array.isArray(currentSEO.keywords)
        ? currentSEO.keywords.join(", ")
        : currentSEO.keywords,
    );
    updateMetaTag("author", currentSEO.author || "Real2AI");

    // Open Graph tags
    updateMetaProperty("og:title", currentSEO.ogTitle || finalTitle);
    updateMetaProperty(
      "og:description",
      currentSEO.ogDescription || currentSEO.description,
    );
    updateMetaProperty(
      "og:image",
      currentSEO.ogImage || "https://real2.ai/images/og-default.jpg",
    );
    updateMetaProperty(
      "og:url",
      currentSEO.ogUrl || `https://real2.ai${location.pathname}`,
    );
    updateMetaProperty("og:type", currentSEO.ogType || "website");
    updateMetaProperty(
      "og:site_name",
      currentSEO.ogSiteName || "Real2AI",
    );

    // Twitter Card tags
    updateMetaTag(
      "twitter:card",
      currentSEO.twitterCard || "summary_large_image",
    );
    updateMetaTag(
      "twitter:site",
      currentSEO.twitterSite || "@Real2AI",
    );
    updateMetaTag(
      "twitter:title",
      currentSEO.twitterTitle || currentSEO.ogTitle || finalTitle,
    );
    updateMetaTag(
      "twitter:description",
      currentSEO.twitterDescription || currentSEO.ogDescription ||
        currentSEO.description,
    );
    updateMetaTag(
      "twitter:image",
      currentSEO.twitterImage || currentSEO.ogImage ||
        "https://real2.ai/images/og-default.jpg",
    );

    // Canonical URL
    updateLinkTag(
      "canonical",
      currentSEO.canonical
        ? `https://real2.ai${currentSEO.canonical}`
        : `https://real2.ai${location.pathname}`,
    );

    // Robots meta tag
    const robotsContent = [];
    if (currentSEO.noIndex) robotsContent.push("noindex");
    else robotsContent.push("index");
    if (currentSEO.noFollow) robotsContent.push("nofollow");
    else robotsContent.push("follow");

    updateMetaTag("robots", robotsContent.join(", "));

    // Structured data
    if (currentSEO.structuredData && currentSEO.structuredData.length > 0) {
      updateStructuredData(currentSEO.structuredData);
    }

    // Track SEO updates
    if (typeof window !== "undefined" && (window as any).gtag) {
      (window as any).gtag("config", "GA_MEASUREMENT_ID", {
        page_title: finalTitle,
        page_location: `https://real2.ai${location.pathname}`,
      });
    }
  }, [currentSEO, location.pathname, isLoading]);

  return {
    seoData: currentSEO,
    updateSEO,
    isLoading,

    // Convenience methods
    setTitle: (title: string) => updateSEO({ title }),
    setDescription: (description: string) => updateSEO({ description }),
    setBreadcrumbs: (breadcrumbs: Array<{ name: string; url: string }>) =>
      updateSEO({ breadcrumbs }),
    setContractAnalysis: (address: string, riskScore?: number) =>
      updateSEO({ address, riskScore }),
    setPropertyIntelligence: (
      suburb: string,
      state: string,
      medianPrice?: string,
    ) => updateSEO({ suburb, state, medianPrice }),
    setMarketAnalysis: (region: string, trend?: string) =>
      updateSEO({ region, trend }),
  };
}

/**
 * Update or create a meta tag
 */
function updateMetaTag(name: string, content?: string) {
  if (!content) return;

  let metaTag = document.querySelector(
    `meta[name="${name}"]`,
  ) as HTMLMetaElement;

  if (!metaTag) {
    metaTag = document.createElement("meta");
    metaTag.name = name;
    document.head.appendChild(metaTag);
  }

  metaTag.content = content;
}

/**
 * Update or create a meta property tag (for Open Graph)
 */
function updateMetaProperty(property: string, content?: string) {
  if (!content) return;

  let metaTag = document.querySelector(
    `meta[property="${property}"]`,
  ) as HTMLMetaElement;

  if (!metaTag) {
    metaTag = document.createElement("meta");
    metaTag.setAttribute("property", property);
    document.head.appendChild(metaTag);
  }

  metaTag.content = content;
}

/**
 * Update or create a link tag
 */
function updateLinkTag(rel: string, href?: string) {
  if (!href) return;

  let linkTag = document.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement;

  if (!linkTag) {
    linkTag = document.createElement("link");
    linkTag.rel = rel;
    document.head.appendChild(linkTag);
  }

  linkTag.href = href;
}

/**
 * Update JSON-LD structured data
 */
function updateStructuredData(
  structuredDataArray?: Array<Record<string, any>>,
) {
  // Remove existing structured data scripts
  const existingScripts = document.querySelectorAll(
    'script[type="application/ld+json"]',
  );
  existingScripts.forEach((script) => script.remove());

  if (!structuredDataArray || structuredDataArray.length === 0) {
    return;
  }

  // Add new structured data scripts
  structuredDataArray.forEach((data, index) => {
    const scriptTag = document.createElement("script");
    scriptTag.type = "application/ld+json";
    scriptTag.id = `structured-data-${index}`;
    scriptTag.textContent = JSON.stringify(data);
    document.head.appendChild(scriptTag);
  });
}

/**
 * Get current page SEO data (useful for debugging)
 */
export function getCurrentSEOData(): SEOData {
  const title = document.title;
  const description = document.querySelector('meta[name="description"]')
    ?.getAttribute("content");
  const keywords = document.querySelector('meta[name="keywords"]')
    ?.getAttribute("content")?.split(", ");
  const ogTitle = document.querySelector('meta[property="og:title"]')
    ?.getAttribute("content");
  const ogDescription = document.querySelector(
    'meta[property="og:description"]',
  )?.getAttribute("content");
  const ogImage = document.querySelector('meta[property="og:image"]')
    ?.getAttribute("content");
  const ogUrl = document.querySelector('meta[property="og:url"]')?.getAttribute(
    "content",
  );
  const ogType = document.querySelector('meta[property="og:type"]')
    ?.getAttribute("content") as SEOData["ogType"];
  const twitterCard = document.querySelector('meta[name="twitter:card"]')
    ?.getAttribute("content") as SEOData["twitterCard"];
  const canonical = document.querySelector('link[rel="canonical"]')
    ?.getAttribute("href");
  const robots = document.querySelector('meta[name="robots"]')?.getAttribute(
    "content",
  );
  const author = document.querySelector('meta[name="author"]')?.getAttribute(
    "content",
  );

  // Get structured data
  const structuredDataScripts = document.querySelectorAll(
    'script[type="application/ld+json"]',
  );
  const structuredData = Array.from(structuredDataScripts)
    .map((script) => {
      try {
        return JSON.parse(script.textContent || "");
      } catch {
        return null;
      }
    })
    .filter(Boolean);

  return {
    title,
    description: description ?? undefined,
    keywords,
    ogTitle: ogTitle ?? undefined,
    ogDescription: ogDescription ?? undefined,
    ogImage: ogImage ?? undefined,
    ogUrl: ogUrl ?? undefined,
    ogType,
    twitterCard,
    canonical: canonical ?? undefined,
    robots: robots ?? undefined,
    author: author ?? undefined,
    structuredData: structuredData.length > 0 ? structuredData : undefined,
    noIndex: robots?.includes("noindex") || false,
    noFollow: robots?.includes("nofollow") || false,
  };
}

/**
 * Validate SEO completeness for current page
 */
export function validateSEO(): {
  valid: boolean;
  missing: string[];
  warnings: string[];
} {
  const missing: string[] = [];
  const warnings: string[] = [];

  // Required elements
  if (!document.title) missing.push("title");
  if (!document.querySelector('meta[name="description"]')) {
    missing.push("description");
  }
  if (!document.querySelector('link[rel="canonical"]')) {
    missing.push("canonical");
  }

  // Recommended elements
  if (!document.querySelector('meta[property="og:title"]')) {
    warnings.push("og:title");
  }
  if (!document.querySelector('meta[property="og:description"]')) {
    warnings.push("og:description");
  }
  if (!document.querySelector('meta[property="og:image"]')) {
    warnings.push("og:image");
  }

  // Content validation
  const titleLength = document.title?.length || 0;
  if (titleLength > 60) warnings.push("title too long (>60 chars)");
  if (titleLength < 30) warnings.push("title too short (<30 chars)");

  const description = document.querySelector('meta[name="description"]')
    ?.getAttribute("content");
  const descLength = description?.length || 0;
  if (descLength > 160) warnings.push("description too long (>160 chars)");
  if (descLength < 120) warnings.push("description too short (<120 chars)");

  return {
    valid: missing.length === 0,
    missing,
    warnings,
  };
}

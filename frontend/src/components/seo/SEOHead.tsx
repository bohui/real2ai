/**
 * SEOHead Component - Dynamic Meta Tag Manager
 * Handles all SEO-related head elements with real-time updates
 * React 19 compatible implementation using native document API
 */

import { useEffect } from 'react';

export interface SEOData {
  // Basic Meta Tags
  title?: string;
  description?: string;
  keywords?: string[];
  canonical?: string;
  
  // Open Graph Tags
  ogTitle?: string;
  ogDescription?: string;
  ogImage?: string;
  ogUrl?: string;
  ogType?: 'website' | 'article' | 'product' | 'profile';
  ogSiteName?: string;
  
  // Twitter Card Tags
  twitterCard?: 'summary' | 'summary_large_image' | 'app' | 'player';
  twitterSite?: string;
  twitterCreator?: string;
  twitterTitle?: string;
  twitterDescription?: string;
  twitterImage?: string;
  
  // Additional Tags
  robots?: string;
  author?: string;
  publisher?: string;
  alternateUrls?: Array<{ href: string; hreflang: string }>;
  
  // Structured Data
  structuredData?: Array<Record<string, any>>;
  
  // Page-specific
  noIndex?: boolean;
  noFollow?: boolean;
  lastModified?: string;
  publishedTime?: string;
  modifiedTime?: string;
  section?: string;
  tags?: string[];
}

interface SEOHeadProps {
  data: SEOData;
  templateTitle?: string;
  titleSeparator?: string;
  defaultImage?: string;
  baseUrl?: string;
}

export const SEOHead: React.FC<SEOHeadProps> = ({
  data,
  templateTitle = 'Real2AI',
  titleSeparator = ' - ',
  defaultImage = 'https://real2.ai/images/og-default.jpg',
  baseUrl = 'https://real2.ai',
}) => {
  const {
    title,
    description,
    keywords,
    canonical,
    ogTitle,
    ogDescription,
    ogImage,
    ogUrl,
    ogType = 'website',
    ogSiteName = 'Real2AI',
    twitterCard = 'summary_large_image',
    twitterSite = '@Real2AI',
    twitterCreator,
    twitterTitle,
    twitterDescription,
    twitterImage,
    robots,
    author,
    publisher,
    alternateUrls,
    structuredData,
    noIndex,
    noFollow,
    lastModified,
    publishedTime,
    modifiedTime,
    section,
    tags,
  } = data;

  // Generate final title
  const finalTitle = title
    ? title.includes(templateTitle)
      ? title
      : `${title}${titleSeparator}${templateTitle}`
    : templateTitle;

  // Generate robots content
  const robotsContent = robots || (() => {
    const robotsArray: string[] = [];
    if (noIndex) robotsArray.push('noindex');
    else robotsArray.push('index');
    if (noFollow) robotsArray.push('nofollow');
    else robotsArray.push('follow');
    return robotsArray.join(', ');
  })();

  // Generate final image URL
  const finalImage = ogImage || twitterImage || defaultImage;
  const finalImageUrl = finalImage.startsWith('http') ? finalImage : `${baseUrl}${finalImage}`;

  // Generate final URL
  const finalUrl = ogUrl || (canonical ? `${baseUrl}${canonical}` : baseUrl);

  // Update document head using native DOM API
  useEffect(() => {
    // Update document title
    document.title = finalTitle;

    // Helper function to update or create meta tags
    const updateMetaTag = (name: string, content?: string, isProperty = false) => {
      if (!content) return;
      
      const selector = isProperty ? `meta[property="${name}"]` : `meta[name="${name}"]`;
      let metaTag = document.querySelector(selector) as HTMLMetaElement;
      
      if (!metaTag) {
        metaTag = document.createElement('meta');
        if (isProperty) {
          metaTag.setAttribute('property', name);
        } else {
          metaTag.name = name;
        }
        document.head.appendChild(metaTag);
      }
      
      metaTag.content = content;
    };

    // Helper function to update or create link tags
    const updateLinkTag = (rel: string, href?: string, hreflang?: string) => {
      if (!href) return;
      
      const selector = hreflang ? `link[rel="${rel}"][hreflang="${hreflang}"]` : `link[rel="${rel}"]`;
      let linkTag = document.querySelector(selector) as HTMLLinkElement;
      
      if (!linkTag) {
        linkTag = document.createElement('link');
        linkTag.rel = rel;
        if (hreflang) linkTag.setAttribute('hreflang', hreflang);
        document.head.appendChild(linkTag);
      }
      
      linkTag.href = href;
    };

    // Basic Meta Tags
    updateMetaTag('description', description);
    updateMetaTag('keywords', keywords?.join(', '));
    updateMetaTag('author', author);
    updateMetaTag('publisher', publisher);
    updateMetaTag('last-modified', lastModified);
    updateMetaTag('robots', robotsContent);

    // Canonical URL
    updateLinkTag('canonical', canonical ? `${baseUrl}${canonical}` : undefined);

    // Alternate URLs
    alternateUrls?.forEach(({ href, hreflang }) => {
      const fullHref = href.startsWith('http') ? href : `${baseUrl}${href}`;
      updateLinkTag('alternate', fullHref, hreflang);
    });

    // Open Graph Tags
    updateMetaTag('og:type', ogType, true);
    updateMetaTag('og:site_name', ogSiteName, true);
    updateMetaTag('og:title', ogTitle || finalTitle, true);
    updateMetaTag('og:description', ogDescription || description, true);
    updateMetaTag('og:image', finalImageUrl, true);
    updateMetaTag('og:image:alt', ogTitle || finalTitle, true);
    updateMetaTag('og:url', finalUrl, true);
    updateMetaTag('og:locale', 'en_AU', true);

    // Article specific tags
    updateMetaTag('article:published_time', publishedTime, true);
    updateMetaTag('article:modified_time', modifiedTime, true);
    updateMetaTag('article:section', section, true);
    updateMetaTag('article:author', author, true);

    // Article tags
    tags?.forEach((tag, index) => {
      updateMetaTag(`article:tag-${index}`, tag, true);
    });

    // Twitter Card Tags
    updateMetaTag('twitter:card', twitterCard);
    updateMetaTag('twitter:site', twitterSite);
    updateMetaTag('twitter:creator', twitterCreator);
    updateMetaTag('twitter:title', twitterTitle || ogTitle || finalTitle);
    updateMetaTag('twitter:description', twitterDescription || ogDescription || description);
    updateMetaTag('twitter:image', finalImageUrl);
    updateMetaTag('twitter:image:alt', ogTitle || finalTitle);

    // Additional SEO Tags
    updateMetaTag('format-detection', 'telephone=no');
    updateMetaTag('theme-color', '#2563eb');
    updateMetaTag('msapplication-TileColor', '#2563eb');
    updateMetaTag('apple-mobile-web-app-capable', 'yes');
    updateMetaTag('apple-mobile-web-app-status-bar-style', 'default');

    // Structured Data
    if (structuredData && structuredData.length > 0) {
      // Remove existing structured data scripts
      document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
        if (script.id?.startsWith('seo-structured-data-')) {
          script.remove();
        }
      });

      // Add new structured data scripts
      structuredData.forEach((data, index) => {
        const scriptTag = document.createElement('script');
        scriptTag.type = 'application/ld+json';
        scriptTag.id = `seo-structured-data-${index}`;
        scriptTag.textContent = JSON.stringify(data);
        document.head.appendChild(scriptTag);
      });
    }

    // Track SEO updates for analytics
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('config', 'GA_MEASUREMENT_ID', {
        page_title: finalTitle,
        page_location: finalUrl,
      });
    }
  }, [
    finalTitle,
    description,
    keywords,
    author,
    publisher,
    lastModified,
    robotsContent,
    canonical,
    baseUrl,
    alternateUrls,
    ogType,
    ogSiteName,
    ogTitle,
    ogDescription,
    finalImageUrl,
    finalUrl,
    publishedTime,
    modifiedTime,
    section,
    tags,
    twitterCard,
    twitterSite,
    twitterCreator,
    twitterTitle,
    twitterDescription,
    structuredData
  ]);

  // This component doesn't render anything visible
  return null;
};

export default SEOHead;
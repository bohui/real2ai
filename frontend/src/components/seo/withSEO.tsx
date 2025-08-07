/**
 * Higher-Order Component for automatic SEO management
 * Provides a convenient way to add SEO to any page component
 */

import React from 'react';
import { useLocation } from 'react-router-dom';
import SEOHead, { SEOData } from './SEOHead';
import { useSEO, DynamicSEOData } from '@/hooks/useSEO';

export interface WithSEOOptions {
  staticSEO?: Partial<SEOData>;
  dynamicSEO?: DynamicSEOData;
  generateSEO?: (pathname: string, data?: any) => Partial<SEOData>;
  baseUrl?: string;
  templateTitle?: string;
  titleSeparator?: string;
  defaultImage?: string;
}

/**
 * HOC that wraps a component with automatic SEO management
 */
export function withSEO<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options: WithSEOOptions = {}
) {
  const WithSEOComponent = React.forwardRef<any, P>((props, ref) => {
    const location = useLocation();
    const {
      staticSEO,
      dynamicSEO,
      generateSEO,
      baseUrl = 'https://real2.ai',
      templateTitle = 'Real2AI',
      titleSeparator = ' - ',
      defaultImage = '/images/og-default.jpg'
    } = options;

    // Generate SEO data
    const customSEO = generateSEO ? generateSEO(location.pathname, props) : staticSEO;
    const { seoData } = useSEO(customSEO, dynamicSEO);

    return (
      <>
        <SEOHead
          data={seoData}
          baseUrl={baseUrl}
          templateTitle={templateTitle}
          titleSeparator={titleSeparator}
          defaultImage={defaultImage}
        />
        <WrappedComponent ref={ref} {...props} />
      </>
    );
  });

  WithSEOComponent.displayName = `withSEO(${WrappedComponent.displayName || WrappedComponent.name})`;
  
  return WithSEOComponent;
}

/**
 * Hook-based alternative to HOC for functional components
 */
export function useSEOForPage(options: WithSEOOptions = {}) {
  const location = useLocation();
  const {
    staticSEO,
    dynamicSEO,
    generateSEO,
    baseUrl = 'https://real2.ai',
    templateTitle = 'Real2AI',
    titleSeparator = ' - ',
    defaultImage = '/images/og-default.jpg'
  } = options;

  const customSEO = generateSEO ? generateSEO(location.pathname) : staticSEO;
  const { seoData, updateSEO } = useSEO(customSEO, dynamicSEO);

  const SEOComponent = React.useMemo(() => (
    <SEOHead
      data={seoData}
      baseUrl={baseUrl}
      templateTitle={templateTitle}
      titleSeparator={titleSeparator}
      defaultImage={defaultImage}
    />
  ), [seoData, baseUrl, templateTitle, titleSeparator, defaultImage]);

  return {
    SEOComponent,
    seoData,
    updateSEO
  };
}

export default withSEO;
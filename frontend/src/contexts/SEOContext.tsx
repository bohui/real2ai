/**
 * SEO Context Provider
 * Manages global SEO state and provides utilities for all components
 */

import React, { createContext, useContext, useCallback, useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { SEOData } from '@/components/seo/SEOHead';
import { DynamicSEOData } from '@/hooks/useSEO';
import { generateSEOData, SEO_CONFIG } from '@/config/seoConfig';

interface SEOContextValue {
  currentSEO: SEOData;
  updateGlobalSEO: (seo: Partial<SEOData>) => void;
  updateDynamicSEO: (data: DynamicSEOData) => void;
  resetSEO: () => void;
  setSEOForRoute: (pathname: string, dynamicData?: DynamicSEOData) => void;
  isLoading: boolean;
}

const SEOContext = createContext<SEOContextValue | null>(null);

export interface SEOProviderProps {
  children: React.ReactNode;
  baseConfig?: {
    baseUrl?: string;
    siteName?: string;
    defaultTitle?: string;
    titleSeparator?: string;
    defaultImage?: string;
  };
}

export function SEOProvider({ children, baseConfig = {} }: SEOProviderProps) {
  const location = useLocation();
  const [currentSEO, setCurrentSEO] = useState<SEOData>({});
  const [isLoading, setIsLoading] = useState(false);

  const config = {
    ...SEO_CONFIG,
    ...baseConfig
  };

  // Generate initial SEO data for current route
  const initializeSEOForRoute = useCallback((pathname: string, dynamicData?: DynamicSEOData) => {
    setIsLoading(true);
    try {
      const seoData = generateSEOData(pathname, dynamicData);
      setCurrentSEO(seoData);
    } catch (error) {
      console.error('Failed to generate SEO data:', error);
      // Fallback to default SEO
      setCurrentSEO({
        title: config.defaultTitle,
        description: config.defaultDescription,
        canonical: pathname
      });
    } finally {
      setIsLoading(false);
    }
  }, [config]);

  // Update SEO when route changes
  useEffect(() => {
    initializeSEOForRoute(location.pathname);
  }, [location.pathname, initializeSEOForRoute]);

  const updateGlobalSEO = useCallback((seo: Partial<SEOData>) => {
    setCurrentSEO(prev => ({
      ...prev,
      ...seo
    }));
  }, []);

  const updateDynamicSEO = useCallback((data: DynamicSEOData) => {
    setIsLoading(true);
    try {
      const generatedSEO = generateSEOData(location.pathname, data);
      setCurrentSEO(prev => ({
        ...prev,
        ...generatedSEO
      }));
    } catch (error) {
      console.error('Failed to update dynamic SEO:', error);
    } finally {
      setIsLoading(false);
    }
  }, [location.pathname]);

  const resetSEO = useCallback(() => {
    initializeSEOForRoute(location.pathname);
  }, [location.pathname, initializeSEOForRoute]);

  const setSEOForRoute = useCallback((pathname: string, dynamicData?: DynamicSEOData) => {
    initializeSEOForRoute(pathname, dynamicData);
  }, [initializeSEOForRoute]);

  const value: SEOContextValue = {
    currentSEO,
    updateGlobalSEO,
    updateDynamicSEO,
    resetSEO,
    setSEOForRoute,
    isLoading
  };

  return (
    <SEOContext.Provider value={value}>
      {children}
    </SEOContext.Provider>
  );
}

export function useSEOContext(): SEOContextValue {
  const context = useContext(SEOContext);
  if (!context) {
    throw new Error('useSEOContext must be used within a SEOProvider');
  }
  return context;
}

/**
 * Custom hook for component-level SEO management with context integration
 */
export function usePageSEO(
  staticSEO?: Partial<SEOData>,
  dynamicData?: DynamicSEOData
) {
  const { updateGlobalSEO, updateDynamicSEO, currentSEO, isLoading } = useSEOContext();

  // Update SEO with static data on mount
  useEffect(() => {
    if (staticSEO && Object.keys(staticSEO).length > 0) {
      updateGlobalSEO(staticSEO);
    }
  }, [staticSEO, updateGlobalSEO]);

  // Update SEO with dynamic data when it changes
  useEffect(() => {
    if (dynamicData && Object.keys(dynamicData).length > 0) {
      updateDynamicSEO(dynamicData);
    }
  }, [dynamicData, updateDynamicSEO]);

  return {
    seoData: currentSEO,
    updateSEO: updateGlobalSEO,
    updateDynamicSEO,
    isLoading,
    
    // Convenience methods
    setTitle: (title: string) => updateGlobalSEO({ title }),
    setDescription: (description: string) => updateGlobalSEO({ description }),
    setKeywords: (keywords: string[]) => updateGlobalSEO({ keywords }),
    setCanonical: (canonical: string) => updateGlobalSEO({ canonical }),
    setOGImage: (ogImage: string) => updateGlobalSEO({ ogImage }),
  };
}

export default SEOProvider;
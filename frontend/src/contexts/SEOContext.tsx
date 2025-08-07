/**
 * SEO Context Provider
 * Manages global SEO state and provides utilities for all components
 */

import React, { createContext, useContext, useCallback, useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { SEOData } from '@/components/seo/SEOHead';
import { DynamicSEOData } from '@/hooks/useSEO';
import { generateSEOData } from '@/config/seoConfig';

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

  const config = useMemo(() => ({
    baseUrl: "https://real2.ai",
    siteName: "Real2AI",
    defaultTitle: "Real2AI - Property Analysis Platform",
    defaultDescription: "Advanced AI-powered property analysis and contract review platform for Australian real estate professionals.",
    titleSeparator: " - ",
    defaultImage: "/images/og-default.jpg",
    ...baseConfig
  }), [baseConfig]);

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
  }, []); // Remove config from dependencies as it's stable

  // Update SEO when route changes
  useEffect(() => {
    initializeSEOForRoute(location.pathname);
  }, [location.pathname]); // Remove initializeSEOForRoute from dependencies

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
  }, []); // Remove location.pathname from dependencies as it's handled by the route change effect

  const resetSEO = useCallback(() => {
    initializeSEOForRoute(location.pathname);
  }, [location.pathname]); // Remove initializeSEOForRoute from dependencies

  const setSEOForRoute = useCallback((pathname: string, dynamicData?: DynamicSEOData) => {
    initializeSEOForRoute(pathname, dynamicData);
  }, []); // Remove initializeSEOForRoute from dependencies

  const value: SEOContextValue = React.useMemo(() => ({
    currentSEO,
    updateGlobalSEO,
    updateDynamicSEO,
    resetSEO,
    setSEOForRoute,
    isLoading
  }), [currentSEO, updateGlobalSEO, updateDynamicSEO, resetSEO, setSEOForRoute, isLoading]);

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
  }, [staticSEO]); // Remove updateGlobalSEO from dependencies

  // Update SEO with dynamic data when it changes
  useEffect(() => {
    if (dynamicData && Object.keys(dynamicData).length > 0) {
      updateDynamicSEO(dynamicData);
    }
  }, [dynamicData]); // Remove updateDynamicSEO from dependencies

  const convenienceMethods = useMemo(() => ({
    setTitle: (title: string) => updateGlobalSEO({ title }),
    setDescription: (description: string) => updateGlobalSEO({ description }),
    setKeywords: (keywords: string[]) => updateGlobalSEO({ keywords }),
    setCanonical: (canonical: string) => updateGlobalSEO({ canonical }),
    setOGImage: (ogImage: string) => updateGlobalSEO({ ogImage }),
  }), [updateGlobalSEO]);

  return {
    seoData: currentSEO,
    updateSEO: updateGlobalSEO,
    updateDynamicSEO,
    isLoading,
    ...convenienceMethods,
  };
}

export default SEOProvider;
/**
 * SEO Context Provider
 * Manages global SEO state and provides utilities for all components
 */

import React, {
  createContext,
  useContext,
  useCallback,
  useState,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { useLocation } from "react-router-dom";
import { SEOData } from "@/components/seo/SEOHead";
import { DynamicSEOData } from "@/hooks/useSEO";
import { generateSEOData } from "@/config/seoConfig";

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

  const config = useMemo(
    () => ({
      baseUrl: "https://real2.ai",
      siteName: "Real2AI",
      defaultTitle: "Real2AI - Property Analysis Platform",
      defaultDescription:
        "Advanced AI-powered property analysis and contract review platform for Australian real estate professionals.",
      titleSeparator: " - ",
      defaultImage: "/images/og-default.jpg",
      ...baseConfig,
    }),
    [baseConfig]
  );

  // Store refs for stable functions
  const configRef = useRef(config);
  const locationRef = useRef(location);

  // Update refs when values change
  useEffect(() => {
    configRef.current = config;
    locationRef.current = location;
  }, [config, location]);

  // Create truly stable functions using refs
  const initializeSEOForRoute = useCallback(
    (pathname: string, dynamicData?: DynamicSEOData) => {
      setIsLoading(true);
      try {
        const seoData = generateSEOData(pathname, dynamicData);
        setCurrentSEO(seoData);
      } catch (error) {
        console.error("Failed to generate SEO data:", error);
        // Fallback to default SEO - use stable references
        setCurrentSEO({
          title: configRef.current.defaultTitle,
          description: configRef.current.defaultDescription,
          canonical: pathname,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [] // No dependencies - function is stable
  );

  // Update SEO when route changes - only depend on pathname
  useEffect(() => {
    initializeSEOForRoute(location.pathname);
  }, [location.pathname]); // Removed initializeSEOForRoute dependency

  const updateGlobalSEO = useCallback((seo: Partial<SEOData>) => {
    setCurrentSEO((prev) => ({
      ...prev,
      ...seo,
    }));
  }, []);

  const updateDynamicSEO = useCallback((data: DynamicSEOData) => {
    setIsLoading(true);
    try {
      const generatedSEO = generateSEOData(locationRef.current.pathname, data);
      setCurrentSEO((prev) => ({
        ...prev,
        ...generatedSEO,
      }));
    } catch (error) {
      console.error("Failed to update dynamic SEO:", error);
    } finally {
      setIsLoading(false);
    }
  }, []); // No dependencies - function is stable

  const resetSEO = useCallback(() => {
    initializeSEOForRoute(locationRef.current.pathname);
  }, []); // No dependencies - function is stable

  const setSEOForRoute = useCallback(
    (pathname: string, dynamicData?: DynamicSEOData) => {
      initializeSEOForRoute(pathname, dynamicData);
    },
    [] // No dependencies - function is stable
  );

  const value: SEOContextValue = React.useMemo(
    () => ({
      currentSEO,
      updateGlobalSEO,
      updateDynamicSEO,
      resetSEO,
      setSEOForRoute,
      isLoading,
    }),
    [
      currentSEO,
      updateGlobalSEO,
      updateDynamicSEO,
      resetSEO,
      setSEOForRoute,
      isLoading,
    ]
  );

  return <SEOContext.Provider value={value}>{children}</SEOContext.Provider>;
}

export function useSEOContext(): SEOContextValue {
  const context = useContext(SEOContext);
  if (!context) {
    throw new Error("useSEOContext must be used within a SEOProvider");
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
  const { updateGlobalSEO, updateDynamicSEO, currentSEO, isLoading } =
    useSEOContext();

  // Use refs to track previous values and only update when content actually changes
  const prevStaticSEORef = useRef<string | undefined>(undefined);
  const prevDynamicDataRef = useRef<string | undefined>(undefined);

  // Update SEO with static data only when content actually changes
  useEffect(() => {
    if (staticSEO && Object.keys(staticSEO).length > 0) {
      const staticSEOString = JSON.stringify(staticSEO);
      if (staticSEOString !== prevStaticSEORef.current) {
        prevStaticSEORef.current = staticSEOString;
        updateGlobalSEO(staticSEO);
      }
    }
  }); // No dependency array - runs every render but only updates when content changes

  // Update SEO with dynamic data only when content actually changes
  useEffect(() => {
    if (dynamicData && Object.keys(dynamicData).length > 0) {
      const dynamicDataString = JSON.stringify(dynamicData);
      if (dynamicDataString !== prevDynamicDataRef.current) {
        prevDynamicDataRef.current = dynamicDataString;
        updateDynamicSEO(dynamicData);
      }
    }
  }); // No dependency array - runs every render but only updates when content changes

  const convenienceMethods = useMemo(
    () => ({
      setTitle: (title: string) => updateGlobalSEO({ title }),
      setDescription: (description: string) => updateGlobalSEO({ description }),
      setKeywords: (keywords: string[]) => updateGlobalSEO({ keywords }),
      setCanonical: (canonical: string) => updateGlobalSEO({ canonical }),
      setOGImage: (ogImage: string) => updateGlobalSEO({ ogImage }),
    }),
    [updateGlobalSEO]
  );

  return {
    seoData: currentSEO,
    updateSEO: updateGlobalSEO,
    updateDynamicSEO,
    isLoading,
    ...convenienceMethods,
  };
}

export default SEOProvider;

/**
 * Root SEO Component
 * Provides base SEO metadata for the entire application
 * Automatically handles route-based SEO updates
 */

import React from 'react';
import { useLocation } from 'react-router-dom';
import SEOHead from './SEOHead';
import { useSEOContext } from '@/contexts/SEOContext';

const RootSEO: React.FC = () => {
  const location = useLocation();
  const { currentSEO } = useSEOContext();

  // Don't render anything if no SEO data is available
  if (!currentSEO || Object.keys(currentSEO).length === 0) {
    return null;
  }

  return (
    <SEOHead 
      data={currentSEO}
      baseUrl="https://real2.ai"
      templateTitle="Real2AI"
      titleSeparator=" - "
      defaultImage="/images/og-default.jpg"
    />
  );
};

export default RootSEO;
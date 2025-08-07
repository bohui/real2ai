/**
 * Cache Efficiency Badge Component
 * Shows cache performance metrics in a compact badge format
 */

import React, { useState, useEffect } from 'react';
import { cacheService } from '../../services/cacheService';

interface CacheEfficiencyMetrics {
  cache_hit_rate: number;
  token_savings: number;
  response_time_improvement: number;
  recent_cache_hits: number;
}

interface CacheEfficiencyBadgeProps {
  className?: string;
  showDetails?: boolean;
}

export const CacheEfficiencyBadge: React.FC<CacheEfficiencyBadgeProps> = ({
  className = '',
  showDetails = false
}) => {
  const [metrics, setMetrics] = useState<CacheEfficiencyMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMetrics();
    
    // Refresh metrics every 5 minutes
    const interval = setInterval(loadMetrics, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const loadMetrics = async () => {
    try {
      setIsLoading(true);
      const data = await cacheService.getCacheEfficiencyMetrics();
      setMetrics(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load cache metrics:', err);
      setError(err instanceof Error ? err.message : 'Failed to load metrics');
    } finally {
      setIsLoading(false);
    }
  };

  const getEfficiencyColor = (rate: number): string => {
    if (rate >= 70) return 'bg-green-100 text-green-800 border-green-200';
    if (rate >= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    if (rate >= 30) return 'bg-orange-100 text-orange-800 border-orange-200';
    return 'bg-red-100 text-red-800 border-red-200';
  };

  const getEfficiencyIcon = (rate: number): string => {
    if (rate >= 70) return '⚡';
    if (rate >= 50) return '🟡';
    if (rate >= 30) return '🟠';
    return '🔴';
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  if (isLoading) {
    return (
      <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-600 ${className}`}>
        <div className="animate-pulse">Loading cache stats...</div>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-600 ${className}`}>
        <span className="mr-1">⚠️</span>
        Cache stats unavailable
      </div>
    );
  }

  const { cache_hit_rate, token_savings, response_time_improvement, recent_cache_hits } = metrics;

  if (showDetails) {
    return (
      <div className={`bg-white rounded-lg border shadow-sm p-4 ${className}`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">Cache Performance</h3>
          <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs border ${getEfficiencyColor(cache_hit_rate)}`}>
            <span className="mr-1">{getEfficiencyIcon(cache_hit_rate)}</span>
            {cache_hit_rate}% Hit Rate
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Tokens Saved</div>
            <div className="font-semibold text-green-600">
              {formatNumber(token_savings)}
            </div>
          </div>
          
          <div>
            <div className="text-gray-500">Speed Improvement</div>
            <div className="font-semibold text-blue-600">
              {response_time_improvement}% faster
            </div>
          </div>
          
          <div className="col-span-2">
            <div className="text-gray-500">Recent Cache Hits</div>
            <div className="font-semibold text-purple-600">
              {recent_cache_hits} this week
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm border ${getEfficiencyColor(cache_hit_rate)} ${className}`}>
      <span className="mr-1">{getEfficiencyIcon(cache_hit_rate)}</span>
      <span className="font-medium">Cache: {cache_hit_rate}%</span>
      {cache_hit_rate > 0 && (
        <span className="ml-2 text-xs opacity-75">
          {formatNumber(token_savings)} tokens saved
        </span>
      )}
    </div>
  );
};

export default CacheEfficiencyBadge;
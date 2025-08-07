/**
 * Property History List Component
 * Displays user's property search history with cache indicators
 */

import React, { useState, useEffect } from 'react';
import { UserPropertyView } from '../../types';
import { cacheService } from '../../services/cacheService';

interface PropertyHistoryListProps {
  className?: string;
  limit?: number;
  onPropertySelect?: (propertyView: UserPropertyView) => void;
}

export const PropertyHistoryList: React.FC<PropertyHistoryListProps> = ({
  className = '',
  limit = 20,
  onPropertySelect
}) => {
  const [history, setHistory] = useState<UserPropertyView[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    loadHistory();
  }, [limit]);

  const loadHistory = async (loadOffset: number = 0) => {
    try {
      setIsLoading(true);
      const response = await cacheService.getPropertyHistory(limit, loadOffset);
      
      if (response.status === 'success') {
        const newHistory = response.data.history;
        
        if (loadOffset === 0) {
          setHistory(newHistory);
        } else {
          setHistory(prev => [...prev, ...newHistory]);
        }
        
        setHasMore(newHistory.length === limit);
        setOffset(loadOffset + newHistory.length);
      }
      
      setError(null);
    } catch (err) {
      console.error('Failed to load property history:', err);
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setIsLoading(false);
    }
  };

  const loadMore = () => {
    if (!isLoading && hasMore) {
      loadHistory(offset);
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const getSourceBadge = (source: string) => {
    const badges = {
      'search': { text: 'Search', color: 'bg-blue-100 text-blue-800', icon: '🔍' },
      'bookmark': { text: 'Bookmarked', color: 'bg-yellow-100 text-yellow-800', icon: '⭐' },
      'analysis': { text: 'Analysis', color: 'bg-purple-100 text-purple-800', icon: '📊' }
    };
    
    const badge = badges[source as keyof typeof badges] || badges.search;
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        <span className="mr-1">{badge.icon}</span>
        {badge.text}
      </span>
    );
  };

  const getPopularityBadge = (popularityScore?: number, accessCount?: number) => {
    if (typeof popularityScore !== 'number' && typeof accessCount !== 'number') {
      return null;
    }

    const score = popularityScore || accessCount || 0;
    let label = 'New';
    let color = 'bg-gray-100 text-gray-800';
    let icon = '📍';

    if (score > 10) {
      label = 'Hot Property 🔥';
      color = 'bg-red-100 text-red-800';
      icon = '🔥';
    } else if (score > 5) {
      label = 'Popular';
      color = 'bg-orange-100 text-orange-800';
      icon = '📈';
    } else if (score > 2) {
      label = 'Trending';
      color = 'bg-yellow-100 text-yellow-800';
      icon = '📊';
    }

    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${color}`}>
        <span className="mr-1">{icon}</span>
        {label}
      </span>
    );
  };

  if (isLoading && history.length === 0) {
    return (
      <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center space-x-4">
              <div className="h-4 bg-gray-200 rounded w-1/3"></div>
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/6"></div>
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
        <div className="text-center">
          <div className="text-red-600 mb-2">⚠️ Error Loading History</div>
          <div className="text-sm text-gray-600">{error}</div>
          <button
            onClick={() => loadHistory()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
        <div className="text-center text-gray-500">
          <div className="text-4xl mb-2">🏠</div>
          <div className="text-lg font-medium">No Property History</div>
          <div className="text-sm">Your property search history will appear here</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      <div className="p-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900">Property Search History</h3>
        <p className="text-sm text-gray-600">Your recent property searches and cached results</p>
      </div>
      
      <div className="divide-y">
        {history.map((propertyView) => (
          <div
            key={propertyView.id}
            className={`p-4 hover:bg-gray-50 transition-colors ${
              onPropertySelect ? 'cursor-pointer' : ''
            }`}
            onClick={() => onPropertySelect?.(propertyView)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3 mb-2">
                  <h4 className="text-sm font-medium text-gray-900">
                    📍 {propertyView.property_address}
                  </h4>
                  {getSourceBadge(propertyView.source)}
                </div>
                
                <div className="flex items-center space-x-4 text-xs text-gray-500">
                  <span>📅 {formatDate(propertyView.viewed_at)}</span>
                  {propertyView.access_count && (
                    <span>👁️ {propertyView.access_count} views</span>
                  )}
                  {propertyView.analysis_result && (
                    <span className="text-green-600">✅ Analysis Available</span>
                  )}
                </div>
              </div>
              
              <div className="flex flex-col items-end space-y-2">
                {getPopularityBadge(propertyView.popularity_score, propertyView.access_count)}
                
                {onPropertySelect && (
                  <button className="text-xs text-blue-600 hover:text-blue-800">
                    View Property →
                  </button>
                )}
              </div>
            </div>
            
            {/* Show preview of analysis result if available */}
            {propertyView.analysis_result && (
              <div className="mt-2 p-2 bg-blue-50 rounded-md text-xs">
                <div className="font-medium text-blue-900 mb-1">Cached Analysis Preview:</div>
                <div className="text-blue-700">
                  {propertyView.analysis_result.estimated_value && (
                    <span className="mr-3">
                      💰 Est. Value: ${propertyView.analysis_result.estimated_value.toLocaleString()}
                    </span>
                  )}
                  {propertyView.analysis_result.risk_level && (
                    <span className="mr-3">
                      ⚠️ Risk: {propertyView.analysis_result.risk_level}
                    </span>
                  )}
                  {propertyView.analysis_result.market_trend && (
                    <span>
                      📈 Trend: {propertyView.analysis_result.market_trend}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {hasMore && (
        <div className="p-4 border-t bg-gray-50">
          <button
            onClick={loadMore}
            disabled={isLoading}
            className="w-full px-4 py-2 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
};

export default PropertyHistoryList;
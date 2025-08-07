/**
 * Contract History List Component
 * Displays user's contract analysis history with cache indicators
 */

import React, { useState, useEffect } from 'react';
import { UserContractView } from '../../types';
import { cacheService } from '../../services/cacheService';

interface ContractHistoryListProps {
  className?: string;
  limit?: number;
  onContractSelect?: (contractView: UserContractView) => void;
}

export const ContractHistoryList: React.FC<ContractHistoryListProps> = ({
  className = '',
  limit = 20,
  onContractSelect
}) => {
  const [history, setHistory] = useState<UserContractView[]>([]);
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
      const response = await cacheService.getContractHistory(limit, loadOffset);
      
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
      console.error('Failed to load contract history:', err);
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
      'upload': { text: 'Uploaded', color: 'bg-blue-100 text-blue-800' },
      'cache_hit': { text: 'Cached ⚡', color: 'bg-green-100 text-green-800' },
      'shared': { text: 'Shared', color: 'bg-purple-100 text-purple-800' }
    };
    
    const badge = badges[source as keyof typeof badges] || badges.upload;
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.text}
      </span>
    );
  };

  const getRiskBadge = (riskScore?: number) => {
    if (typeof riskScore !== 'number') return null;
    
    let color = 'bg-gray-100 text-gray-800';
    let label = 'Unknown';
    
    if (riskScore <= 3) {
      color = 'bg-green-100 text-green-800';
      label = 'Low Risk';
    } else if (riskScore <= 6) {
      color = 'bg-yellow-100 text-yellow-800';
      label = 'Medium Risk';
    } else if (riskScore <= 8) {
      color = 'bg-orange-100 text-orange-800';
      label = 'High Risk';
    } else {
      color = 'bg-red-100 text-red-800';
      label = 'Critical Risk';
    }
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${color}`}>
        {label} ({riskScore.toFixed(1)})
      </span>
    );
  };

  if (isLoading && history.length === 0) {
    return (
      <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center space-x-4">
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/3"></div>
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
          <div className="text-4xl mb-2">📄</div>
          <div className="text-lg font-medium">No Contract History</div>
          <div className="text-sm">Your contract analysis history will appear here</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      <div className="p-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900">Contract Analysis History</h3>
        <p className="text-sm text-gray-600">Your recent contract analyses and cached results</p>
      </div>
      
      <div className="divide-y">
        {history.map((contractView) => (
          <div
            key={contractView.id}
            className={`p-4 hover:bg-gray-50 transition-colors ${
              onContractSelect ? 'cursor-pointer' : ''
            }`}
            onClick={() => onContractSelect?.(contractView)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3 mb-2">
                  <h4 className="text-sm font-medium text-gray-900 truncate">
                    {contractView.original_filename || 'Unknown Document'}
                  </h4>
                  {getSourceBadge(contractView.source)}
                </div>
                
                {contractView.property_address && (
                  <div className="text-sm text-gray-600 mb-1">
                    📍 {contractView.property_address}
                  </div>
                )}
                
                <div className="flex items-center space-x-4 text-xs text-gray-500">
                  <span>📅 {formatDate(contractView.viewed_at)}</span>
                  {contractView.file_size && (
                    <span>📏 {(contractView.file_size / 1024 / 1024).toFixed(1)} MB</span>
                  )}
                  {contractView.analysis_status && (
                    <span className="capitalize">Status: {contractView.analysis_status}</span>
                  )}
                </div>
              </div>
              
              <div className="flex flex-col items-end space-y-2">
                {getRiskBadge(contractView.risk_score)}
                
                {onContractSelect && (
                  <button className="text-xs text-blue-600 hover:text-blue-800">
                    View Analysis →
                  </button>
                )}
              </div>
            </div>
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

export default ContractHistoryList;
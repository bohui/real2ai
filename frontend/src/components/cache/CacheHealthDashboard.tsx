/**
 * Cache Health Dashboard Component
 * Administrative dashboard for monitoring cache health and performance
 */

import React, { useState, useEffect } from 'react';
import { CacheHealthStatus, CacheStats } from '../../types';
import { cacheService } from '../../services/cacheService';

interface CacheHealthDashboardProps {
  className?: string;
  isAdmin?: boolean;
}

export const CacheHealthDashboard: React.FC<CacheHealthDashboardProps> = ({
  className = '',
  isAdmin = false
}) => {
  const [healthStatus, setHealthStatus] = useState<CacheHealthStatus | null>(null);
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  useEffect(() => {
    loadHealthData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadHealthData, 30 * 1000);
    return () => clearInterval(interval);
  }, []);

  const loadHealthData = async () => {
    try {
      setIsLoading(true);
      const [healthResponse, statsResponse] = await Promise.all([
        cacheService.getCacheHealth(),
        cacheService.getCacheStats()
      ]);
      
      if (healthResponse.status === 'success' || healthResponse.status === 'error') {
        setHealthStatus(healthResponse.data);
      }
      
      if (statsResponse.status === 'success') {
        setStats(statsResponse.data);
      }
      
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      console.error('Failed to load cache health data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCleanup = async () => {
    if (!isAdmin) return;
    
    try {
      setIsLoading(true);
      await cacheService.cleanupCache();
      await loadHealthData(); // Refresh data after cleanup
    } catch (err) {
      console.error('Cache cleanup failed:', err);
      setError(err instanceof Error ? err.message : 'Cleanup failed');
    } finally {
      setIsLoading(false);
    }
  };

  const getHealthStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthStatusIcon = (status: string): string => {
    switch (status) {
      case 'healthy': return '✅';
      case 'warning': return '⚠️';
      case 'critical': return '❌';
      default: return '❓';
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  if (isLoading && !healthStatus && !stats) {
    return (
      <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error && !healthStatus && !stats) {
    return (
      <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
        <div className="text-center">
          <div className="text-red-600 mb-2">⚠️ Error Loading Cache Health</div>
          <div className="text-sm text-gray-600">{error}</div>
          <button
            onClick={loadHealthData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Cache Health Dashboard</h3>
            <p className="text-sm text-gray-600">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            {healthStatus && (
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${getHealthStatusColor(healthStatus.health_status)}`}>
                <span className="mr-1">{getHealthStatusIcon(healthStatus.health_status)}</span>
                {healthStatus.health_status.toUpperCase()}
              </div>
            )}
            
            <button
              onClick={loadHealthData}
              disabled={isLoading}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
            >
              {isLoading ? '🔄' : '🔄'} Refresh
            </button>
            
            {isAdmin && (
              <button
                onClick={handleCleanup}
                disabled={isLoading}
                className="px-3 py-1 text-sm bg-orange-100 hover:bg-orange-200 text-orange-800 rounded-md transition-colors disabled:opacity-50"
              >
                🧹 Cleanup
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Health Score */}
      {healthStatus && (
        <div className="p-6 border-b">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-gray-900">Health Score</h4>
            <div className="text-2xl font-bold text-gray-900">
              {healthStatus.health_score}/100
            </div>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                healthStatus.health_score >= 80 ? 'bg-green-500' :
                healthStatus.health_score >= 60 ? 'bg-yellow-500' :
                'bg-red-500'
              }`}
              style={{ width: `${healthStatus.health_score}%` }}
            />
          </div>
          
          {/* Issues and Warnings */}
          {(healthStatus.issues.length > 0 || healthStatus.health_status !== 'healthy') && (
            <div className="mt-4 space-y-2">
              {healthStatus.issues.map((issue, index) => (
                <div key={index} className="flex items-start space-x-2 text-sm">
                  <span className="text-red-500 mt-0.5">❌</span>
                  <span className="text-red-700">{issue}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cache Statistics */}
      {stats && (
        <div className="p-6">
          <h4 className="font-medium text-gray-900 mb-4">Cache Statistics</h4>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Contract Cache Stats */}
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h5 className="text-sm font-medium text-blue-900">Contract Cache</h5>
                <span className="text-2xl">📄</span>
              </div>
              <div className="text-2xl font-bold text-blue-600">
                {formatNumber(stats.contracts.total_cached)}
              </div>
              <div className="text-xs text-blue-600">
                Avg {stats.contracts.average_access.toFixed(1)} accesses
              </div>
            </div>

            {/* Property Cache Stats */}
            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h5 className="text-sm font-medium text-green-900">Property Cache</h5>
                <span className="text-2xl">🏠</span>
              </div>
              <div className="text-2xl font-bold text-green-600">
                {formatNumber(stats.properties.total_cached)}
              </div>
              <div className="text-xs text-green-600">
                Score {stats.properties.average_popularity.toFixed(1)}
              </div>
            </div>

            {/* Total Performance */}
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h5 className="text-sm font-medium text-purple-900">Total Performance</h5>
                <span className="text-2xl">⚡</span>
              </div>
              <div className="text-2xl font-bold text-purple-600">
                {formatNumber(
                  stats.contracts.total_cached + stats.properties.total_cached
                )}
              </div>
              <div className="text-xs text-purple-600">
                Total cached items
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hash Consistency */}
      {healthStatus && Object.keys(healthStatus.consistency).length > 0 && (
        <div className="p-6 border-t">
          <h4 className="font-medium text-gray-900 mb-4">Hash Consistency</h4>
          
          <div className="space-y-3">
            {Object.entries(healthStatus.consistency).map(([tableName, data]) => (
              <div key={tableName} className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-900 capitalize">
                    {tableName.replace('_', ' ')}
                  </div>
                  <div className="text-xs text-gray-600">
                    {data.records_with_hashes} / {data.total_records} records
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className={`text-sm font-medium ${
                    data.consistency_percentage >= 95 ? 'text-green-600' :
                    data.consistency_percentage >= 90 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {data.consistency_percentage.toFixed(1)}%
                  </div>
                  
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        data.consistency_percentage >= 95 ? 'bg-green-500' :
                        data.consistency_percentage >= 90 ? 'bg-yellow-500' :
                        'bg-red-500'
                      }`}
                      style={{ width: `${data.consistency_percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CacheHealthDashboard;
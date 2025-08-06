import api from './api';
import {
  PropertySearchRequest,
  PropertySearchResponse,
  PropertyAnalyticsRequest,
  PropertyAnalyticsResponse,
  BulkPropertyAnalysisRequest,
  PropertyProfile,
  PropertyMarketInsight,
  PropertyComparisonResult,
  PropertyWatchlistItem
} from '../types';

export class PropertyIntelligenceService {
  private static instance: PropertyIntelligenceService;
  private baseUrl = '/api/property-intelligence';

  public static getInstance(): PropertyIntelligenceService {
    if (!PropertyIntelligenceService.instance) {
      PropertyIntelligenceService.instance = new PropertyIntelligenceService();
    }
    return PropertyIntelligenceService.instance;
  }

  /**
   * Advanced property search with intelligent filtering
   */
  async searchProperties(request: PropertySearchRequest): Promise<PropertySearchResponse> {
    try {
      const response = await api.post(`${this.baseUrl}/search`, request);
      return response.data;
    } catch (error) {
      console.error('Property search failed:', error);
      throw new Error('Failed to search properties');
    }
  }

  /**
   * Comprehensive property analysis
   */
  async analyzeProperty(request: PropertyAnalyticsRequest): Promise<PropertyAnalyticsResponse> {
    try {
      const response = await api.post(`${this.baseUrl}/analyze`, request);
      return response.data;
    } catch (error) {
      console.error('Property analysis failed:', error);
      throw new Error('Failed to analyze property');
    }
  }

  /**
   * Bulk property portfolio analysis
   */
  async bulkAnalyzeProperties(request: BulkPropertyAnalysisRequest): Promise<any> {
    try {
      const response = await api.post(`${this.baseUrl}/bulk-analyze`, request);
      return response.data;
    } catch (error) {
      console.error('Bulk analysis failed:', error);
      throw new Error('Failed to perform bulk analysis');
    }
  }

  /**
   * Get user's property watchlist
   */
  async getWatchlist(limit: number = 50, offset: number = 0): Promise<PropertyWatchlistItem[]> {
    try {
      const response = await api.get(`${this.baseUrl}/watchlist`, {
        params: { limit, offset }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get watchlist:', error);
      throw new Error('Failed to retrieve property watchlist');
    }
  }

  /**
   * Add property to watchlist
   */
  async addToWatchlist(property: {
    address: string;
    notes?: string;
    tags?: string[];
    alert_preferences?: Record<string, any>;
  }): Promise<any> {
    try {
      const response = await api.post(`${this.baseUrl}/watchlist`, property);
      return response.data;
    } catch (error) {
      console.error('Failed to add to watchlist:', error);
      throw new Error('Failed to add property to watchlist');
    }
  }

  /**
   * Remove property from watchlist
   */
  async removeFromWatchlist(watchlistItemId: string): Promise<void> {
    try {
      await api.delete(`${this.baseUrl}/watchlist/${watchlistItemId}`);
    } catch (error) {
      console.error('Failed to remove from watchlist:', error);
      throw new Error('Failed to remove property from watchlist');
    }
  }

  /**
   * Get market insights for location
   */
  async getMarketInsights(
    location: string,
    insightTypes: string[] = ['trends', 'forecasts'],
    limit: number = 10
  ): Promise<PropertyMarketInsight[]> {
    try {
      const response = await api.get(`${this.baseUrl}/market-insights`, {
        params: { 
          location, 
          insight_types: insightTypes,
          limit 
        }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get market insights:', error);
      throw new Error('Failed to retrieve market insights');
    }
  }

  /**
   * Compare multiple properties
   */
  async compareProperties(
    properties: string[],
    comparisonCriteria: string[] = ['price', 'investment', 'growth']
  ): Promise<PropertyComparisonResult> {
    try {
      const response = await api.post(`${this.baseUrl}/compare`, null, {
        params: {
          properties,
          comparison_criteria: comparisonCriteria
        }
      });
      return response.data;
    } catch (error) {
      console.error('Property comparison failed:', error);
      throw new Error('Failed to compare properties');
    }
  }

  /**
   * Export property data in various formats
   */
  async exportPropertyData(
    format: 'csv' | 'json' | 'pdf',
    properties: string[]
  ): Promise<Blob> {
    try {
      const response = await api.get(`${this.baseUrl}/export/${format}`, {
        params: { properties },
        responseType: 'blob'
      });
      return response.data;
    } catch (error) {
      console.error('Export failed:', error);
      throw new Error('Failed to export property data');
    }
  }

  /**
   * Get property analysis by ID
   */
  async getPropertyAnalysis(propertyId: string): Promise<PropertyProfile> {
    try {
      const response = await api.get(`${this.baseUrl}/property/${propertyId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get property analysis:', error);
      throw new Error('Failed to retrieve property analysis');
    }
  }

  /**
   * Get market analysis for suburb
   */
  async getMarketAnalysis(
    suburb: string,
    state: string,
    propertyType?: string
  ): Promise<any> {
    try {
      const response = await api.get(`${this.baseUrl}/market-analysis`, {
        params: { suburb, state, property_type: propertyType }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get market analysis:', error);
      throw new Error('Failed to retrieve market analysis');
    }
  }

  /**
   * Get investment opportunities for location
   */
  async getInvestmentOpportunities(
    location: string,
    budgetRange?: [number, number],
    investmentStrategy: string = 'growth'
  ): Promise<any> {
    try {
      const response = await api.get(`${this.baseUrl}/investment-opportunities`, {
        params: {
          location,
          budget_min: budgetRange?.[0],
          budget_max: budgetRange?.[1],
          strategy: investmentStrategy
        }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get investment opportunities:', error);
      throw new Error('Failed to retrieve investment opportunities');
    }
  }

  /**
   * Get property valuation
   */
  async getPropertyValuation(
    address: string,
    valuationType: 'avm' | 'desktop' | 'professional' = 'avm'
  ): Promise<any> {
    try {
      const response = await api.post(`${this.baseUrl}/valuation`, {
        address,
        valuation_type: valuationType
      });
      return response.data;
    } catch (error) {
      console.error('Property valuation failed:', error);
      throw new Error('Failed to get property valuation');
    }
  }

  /**
   * Get suburb statistics
   */
  async getSuburbStatistics(suburb: string, state: string): Promise<any> {
    try {
      const response = await api.get(`${this.baseUrl}/suburb-stats`, {
        params: { suburb, state }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get suburb statistics:', error);
      throw new Error('Failed to retrieve suburb statistics');
    }
  }

  /**
   * Search properties with advanced filters
   */
  async searchPropertiesAdvanced(filters: {
    location?: string;
    minPrice?: number;
    maxPrice?: number;
    propertyTypes?: string[];
    minBedrooms?: number;
    maxBedrooms?: number;
    features?: string[];
    sortBy?: string;
    limit?: number;
  }): Promise<PropertySearchResponse> {
    try {
      const searchRequest: PropertySearchRequest = {
        query: filters.location,
        filters: {
          min_price: filters.minPrice,
          max_price: filters.maxPrice,
          property_types: filters.propertyTypes || [],
          min_bedrooms: filters.minBedrooms,
          max_bedrooms: filters.maxBedrooms,
          features_required: filters.features || [],
          suburbs: [],
          states: [],
          min_carspaces: undefined,
          min_bathrooms: undefined,
          max_bathrooms: undefined,
          min_land_area: undefined,
          max_land_area: undefined
        },
        location: filters.location,
        radius_km: 5.0,
        limit: filters.limit || 20,
        sort_by: (filters.sortBy as any) || 'relevance',
        include_off_market: false,
        include_historical: false
      };

      return await this.searchProperties(searchRequest);
    } catch (error) {
      console.error('Advanced property search failed:', error);
      throw new Error('Failed to search properties with advanced filters');
    }
  }

  /**
   * Get property price history
   */
  async getPropertyPriceHistory(propertyId: string): Promise<any> {
    try {
      const response = await api.get(`${this.baseUrl}/property/${propertyId}/price-history`);
      return response.data;
    } catch (error) {
      console.error('Failed to get price history:', error);
      throw new Error('Failed to retrieve property price history');
    }
  }

  /**
   * Get rental estimates for property
   */
  async getRentalEstimate(address: string): Promise<any> {
    try {
      const response = await api.post(`${this.baseUrl}/rental-estimate`, { address });
      return response.data;
    } catch (error) {
      console.error('Failed to get rental estimate:', error);
      throw new Error('Failed to retrieve rental estimate');
    }
  }

  /**
   * Get property report (PDF)
   */
  async generatePropertyReport(
    propertyId: string,
    reportType: 'basic' | 'standard' | 'premium' = 'standard'
  ): Promise<Blob> {
    try {
      const response = await api.post(`${this.baseUrl}/property/${propertyId}/report`, {
        report_type: reportType
      }, {
        responseType: 'blob'
      });
      return response.data;
    } catch (error) {
      console.error('Failed to generate property report:', error);
      throw new Error('Failed to generate property report');
    }
  }

  /**
   * Get nearby amenities for property
   */
  async getNearbyAmenities(
    address: string,
    radius: number = 2000
  ): Promise<any> {
    try {
      const response = await api.get(`${this.baseUrl}/nearby-amenities`, {
        params: { address, radius }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get nearby amenities:', error);
      throw new Error('Failed to retrieve nearby amenities');
    }
  }

  /**
   * Get school catchments for property
   */
  async getSchoolCatchments(address: string): Promise<any> {
    try {
      const response = await api.get(`${this.baseUrl}/school-catchments`, {
        params: { address }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get school catchments:', error);
      throw new Error('Failed to retrieve school catchments');
    }
  }

  /**
   * Get property ownership history
   */
  async getOwnershipHistory(propertyId: string): Promise<any> {
    try {
      const response = await api.get(`${this.baseUrl}/property/${propertyId}/ownership-history`);
      return response.data;
    } catch (error) {
      console.error('Failed to get ownership history:', error);
      throw new Error('Failed to retrieve property ownership history');
    }
  }
}

// Export singleton instance
export const propertyIntelligenceService = PropertyIntelligenceService.getInstance();
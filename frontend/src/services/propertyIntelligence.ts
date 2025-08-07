import apiService from "./api";
import {
  BulkPropertyAnalysisRequest,
  PropertyAnalyticsRequest,
  PropertyAnalyticsResponse,
  PropertyComparisonResult,
  PropertyMarketInsight,
  PropertyProfile,
  PropertySearchRequest,
  PropertySearchResponse,
  PropertyWatchlistItem,
  AlertPreferences
} from "../types";

export class PropertyIntelligenceService {
  private static instance: PropertyIntelligenceService;
  private baseUrl = "/api/property-intelligence";

  public static getInstance(): PropertyIntelligenceService {
    if (!PropertyIntelligenceService.instance) {
      PropertyIntelligenceService.instance = new PropertyIntelligenceService();
    }
    return PropertyIntelligenceService.instance;
  }

  /**
   * Advanced property search with intelligent filtering
   */
  async searchProperties(
    request: PropertySearchRequest,
  ): Promise<PropertySearchResponse> {
    try {
      const response = await apiService.post(`${this.baseUrl}/search`, request);
      return response.data;
    } catch (error) {
      console.error("Property search failed:", error);
      throw new Error("Failed to search properties");
    }
  }

  /**
   * Comprehensive property analysis
   */
  async analyzeProperty(
    request: PropertyAnalyticsRequest,
  ): Promise<PropertyAnalyticsResponse> {
    try {
      const response = await apiService.post(
        `${this.baseUrl}/analyze`,
        request,
      );
      return response.data;
    } catch (error) {
      console.error("Property analysis failed:", error);
      throw new Error("Failed to analyze property");
    }
  }

  /**
   * Bulk property portfolio analysis
   */
  async bulkAnalyzeProperties(
    request: BulkPropertyAnalysisRequest,
  ): Promise<unknown> {
    try {
      const response = await apiService.post(
        `${this.baseUrl}/bulk-analyze`,
        request,
      );
      return response.data;
    } catch (error) {
      console.error("Bulk analysis failed:", error);
      throw new Error("Failed to perform bulk analysis");
    }
  }

  /**
   * Get user's property watchlist
   */
  async getWatchlist(
    limit: number = 50,
    offset: number = 0,
  ): Promise<PropertyWatchlistItem[]> {
    try {
      const response = await apiService.get(`${this.baseUrl}/watchlist`, {
        params: { limit, offset },
      });
      return response.data;
    } catch (error) {
      console.error("Failed to get watchlist:", error);
      throw new Error("Failed to retrieve property watchlist");
    }
  }

  /**
   * Add property to watchlist
   */
  async addToWatchlist(property: {
    address: string;
    notes?: string;
    tags?: string[];
    alert_preferences?: AlertPreferences;
  }): Promise<unknown> {
    try {
      const response = await apiService.post(
        `${this.baseUrl}/watchlist`,
        property,
      );
      return response.data;
    } catch (error) {
      console.error("Failed to add to watchlist:", error);
      throw new Error("Failed to add property to watchlist");
    }
  }

  /**
   * Remove property from watchlist
   */
  async removeFromWatchlist(watchlistItemId: string): Promise<void> {
    try {
      await apiService.delete(`${this.baseUrl}/watchlist/${watchlistItemId}`);
    } catch (error) {
      console.error("Failed to remove from watchlist:", error);
      throw new Error("Failed to remove property from watchlist");
    }
  }

  /**
   * Get market insights for location
   */
  async getMarketInsights(
    location: string,
    insightTypes: string[] = ["trends", "forecasts"],
    limit: number = 10,
  ): Promise<PropertyMarketInsight[]> {
    try {
      const response = await apiService.get(`${this.baseUrl}/market-insights`, {
        params: { location, insight_types: insightTypes.join(","), limit },
      });
      return response.data;
    } catch (error) {
      console.error("Failed to get market insights:", error);
      throw new Error("Failed to retrieve market insights");
    }
  }

  /**
   * Compare multiple properties
   */
  async compareProperties(
    properties: string[],
    comparisonCriteria: string[] = ["price", "investment", "growth"],
  ): Promise<PropertyComparisonResult> {
    try {
      const response = await apiService.post(`${this.baseUrl}/compare`, {
        properties,
        comparison_criteria: comparisonCriteria,
      });
      return response.data;
    } catch (error) {
      console.error("Property comparison failed:", error);
      throw new Error("Failed to compare properties");
    }
  }

  /**
   * Export property data in various formats
   */
  async exportPropertyData(
    format: "csv" | "json" | "pdf",
    properties: string[],
  ): Promise<Blob> {
    try {
      const response = await apiService.post(`${this.baseUrl}/export`, {
        format,
        properties,
      }, {
        responseType: "blob",
      });
      return response.data;
    } catch (error) {
      console.error("Export failed:", error);
      throw new Error("Failed to export property data");
    }
  }

  /**
   * Get comprehensive property analysis
   */
  async getPropertyAnalysis(propertyId: string): Promise<PropertyProfile> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/property/${propertyId}/analysis`,
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get property analysis:", error);
      throw new Error("Failed to retrieve property analysis");
    }
  }

  /**
   * Get market analysis for suburb
   */
  async getMarketAnalysis(
    suburb: string,
    state: string,
    propertyType?: string,
  ): Promise<unknown> {
    try {
      const response = await apiService.get(`${this.baseUrl}/market-analysis`, {
        params: { suburb, state, property_type: propertyType },
      });
      return response.data;
    } catch (error) {
      console.error("Failed to get market analysis:", error);
      throw new Error("Failed to retrieve market analysis");
    }
  }

  /**
   * Get investment opportunities
   */
  async getInvestmentOpportunities(
    location: string,
    budgetRange?: [number, number],
    investmentStrategy: string = "growth",
  ): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/investment-opportunities`,
        {
          params: {
            location,
            min_budget: budgetRange?.[0],
            max_budget: budgetRange?.[1],
            strategy: investmentStrategy,
          },
        },
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get investment opportunities:", error);
      throw new Error("Failed to retrieve investment opportunities");
    }
  }

  /**
   * Get property valuation
   */
  async getPropertyValuation(
    address: string,
    valuationType: "avm" | "desktop" | "professional" = "avm",
  ): Promise<unknown> {
    try {
      const response = await apiService.post(`${this.baseUrl}/valuation`, {
        address,
        valuation_type: valuationType,
      });
      return response.data;
    } catch (error) {
      console.error("Failed to get property valuation:", error);
      throw new Error("Failed to retrieve property valuation");
    }
  }

  /**
   * Get suburb statistics
   */
  async getSuburbStatistics(suburb: string, state: string): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/suburb-statistics`,
        {
          params: { suburb, state },
        },
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get suburb statistics:", error);
      throw new Error("Failed to retrieve suburb statistics");
    }
  }

  /**
   * Advanced property search with filters
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
          suburbs: filters.location ? [filters.location] : [],
          states: [],
          min_carspaces: undefined,
          min_land_area: undefined,
          max_land_area: undefined,
        },
        location: filters.location,
        radius_km: 50,
        limit: filters.limit || 20,
        sort_by: (filters.sortBy as PropertySearchRequest['sort_by']) || "relevance",
        include_off_market: false,
        include_historical: false,
      };

      return await this.searchProperties(searchRequest);
    } catch (error) {
      console.error("Advanced property search failed:", error);
      throw new Error("Failed to search properties with advanced filters");
    }
  }

  /**
   * Get property price history
   */
  async getPropertyPriceHistory(propertyId: string): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/property/${propertyId}/price-history`,
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get price history:", error);
      throw new Error("Failed to retrieve property price history");
    }
  }

  /**
   * Get rental estimates for property
   */
  async getRentalEstimate(address: string): Promise<unknown> {
    try {
      const response = await apiService.post(
        `${this.baseUrl}/rental-estimate`,
        { address },
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get rental estimate:", error);
      throw new Error("Failed to retrieve rental estimate");
    }
  }

  /**
   * Get property report (PDF)
   */
  async generatePropertyReport(
    propertyId: string,
    reportType: "basic" | "standard" | "premium" = "standard",
  ): Promise<Blob> {
    try {
      const response = await apiService.post(
        `${this.baseUrl}/property/${propertyId}/report`,
        {
          report_type: reportType,
        },
        {
          responseType: "blob",
        },
      );
      return response.data;
    } catch (error) {
      console.error("Failed to generate property report:", error);
      throw new Error("Failed to generate property report");
    }
  }

  /**
   * Get nearby amenities for property
   */
  async getNearbyAmenities(
    address: string,
    radius: number = 2000,
  ): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/nearby-amenities`,
        {
          params: { address, radius },
        },
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get nearby amenities:", error);
      throw new Error("Failed to retrieve nearby amenities");
    }
  }

  /**
   * Get school catchments for property
   */
  async getSchoolCatchments(address: string): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/school-catchments`,
        {
          params: { address },
        },
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get school catchments:", error);
      throw new Error("Failed to retrieve school catchments");
    }
  }

  /**
   * Get property ownership history
   */
  async getOwnershipHistory(propertyId: string): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/property/${propertyId}/ownership-history`,
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get ownership history:", error);
      throw new Error("Failed to retrieve property ownership history");
    }
  }

  /**
   * Get market trends data
   */
  async getMarketTrends(
    timeframe: "3M" | "6M" | "1Y" | "2Y" = "1Y",
  ): Promise<unknown> {
    try {
      const response = await apiService.get(`${this.baseUrl}/market-trends`, {
        params: { timeframe },
      });
      return response.data;
    } catch (error) {
      console.error("Failed to get market trends:", error);
      throw new Error("Failed to retrieve market trends");
    }
  }

  /**
   * Get national market statistics
   */
  async getNationalMarketStats(): Promise<unknown> {
    try {
      const response = await apiService.get(`${this.baseUrl}/market/national`);
      return response.data;
    } catch (error) {
      console.error("Failed to get national market stats:", error);
      throw new Error("Failed to retrieve national market statistics");
    }
  }

  /**
   * Get state market comparison data
   */
  async getStateMarketComparison(): Promise<unknown> {
    try {
      const response = await apiService.get(`${this.baseUrl}/market/states`);
      return response.data;
    } catch (error) {
      console.error("Failed to get state market comparison:", error);
      throw new Error("Failed to retrieve state market comparison");
    }
  }

  /**
   * Get high growth suburbs
   */
  async getHotSuburbs(limit: number = 10): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/market/hot-suburbs`,
        {
          params: { limit },
        },
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get hot suburbs:", error);
      throw new Error("Failed to retrieve high growth suburbs");
    }
  }

  /**
   * Get market predictions
   */
  async getMarketPredictions(): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/market/predictions`,
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get market predictions:", error);
      throw new Error("Failed to retrieve market predictions");
    }
  }

  /**
   * Get market risk factors
   */
  async getMarketRiskFactors(): Promise<unknown> {
    try {
      const response = await apiService.get(
        `${this.baseUrl}/market/risk-factors`,
      );
      return response.data;
    } catch (error) {
      console.error("Failed to get market risk factors:", error);
      throw new Error("Failed to retrieve market risk factors");
    }
  }
}

// Export singleton instance
export const propertyIntelligenceService = PropertyIntelligenceService
  .getInstance();

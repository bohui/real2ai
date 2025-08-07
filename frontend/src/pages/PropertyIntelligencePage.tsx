import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  TrendingUp,
  AlertTriangle,
  Bookmark,
  BookmarkCheck,
  Filter,
  BarChart3,
  Calculator,
  Bell,
  Star,
  Building,
  ShieldCheck,
  Calendar,
} from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import StatusBadge from "@/components/ui/StatusBadge";
import { cn } from "@/utils";
import { usePageSEO } from "@/contexts/SEOContext";
import { propertyIntelligenceService } from "@/services/propertyIntelligence";
import {
  PropertySearchRequest,
  PropertyListing,
  PropertyWatchlistItem,
} from "@/types";

// Property display interface for UI compatibility
interface PropertyDisplay {
  id: string;
  address: string;
  suburb?: string;
  state?: string;
  propertyType: string;
  bedrooms: number;
  bathrooms: number;
  carSpaces: number;
  currentValue: number;
  confidence?: number;
  riskScore?: number;
  investmentScore: number;
  growthRate?: number;
  yield?: number;
  isSaved: boolean;
  lastUpdated?: string;
  priceChange?: number;
  daysOnMarket?: number;
  schoolScore?: number;
  amenityScore?: number;
  transportScore?: number;
  environmentalRisk?: string;
  estimated_rental?: number;
}

interface MarketInsights {
  nationalGrowth: number;
  interestRate: number;
  averageSettlement: number;
  hotSuburbs: string[];
  marketTrend: string;
  confidenceIndex: number;
}

const PropertyIntelligencePage: React.FC = () => {
  // UI State
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedView, setSelectedView] = useState<"grid" | "list">("grid");
  const [showFilters, setShowFilters] = useState(false);

  // SEO for Property Intelligence page
  usePageSEO(
    {
      title: 'Property Intelligence - Real2AI',
      description: 'Comprehensive property intelligence powered by AI. Market analysis, price trends, suburb insights, and investment potential for Australian real estate.',
      keywords: [
        'property intelligence',
        'real estate data',
        'market analysis',
        'property prices',
        'Australian property market',
        'suburb analysis',
        'investment insights'
      ],
      canonical: '/app/property-intelligence',
      noIndex: true // Private property intelligence page
    },
    searchQuery ? {
      suburb: searchQuery.split(',')[0]?.trim(),
      state: searchQuery.split(',')[1]?.trim(),
    } : undefined
  );

  // Data State
  const [properties, setProperties] = useState<PropertyDisplay[]>([]);
  const [marketInsights, setMarketInsights] = useState<MarketInsights | null>(
    null
  );
  const [watchlist, setWatchlist] = useState<PropertyWatchlistItem[]>([]);

  // Loading and Error States
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter States
  const [filters, setFilters] = useState({
    propertyType: "",
    bedrooms: "",
    priceRange: "",
    riskLevel: "",
  });

  // Saved properties from watchlist
  const [savedProperties, setSavedProperties] = useState<string[]>([]);

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      // Load watchlist
      const watchlistData = await propertyIntelligenceService.getWatchlist(50);
      setWatchlist(watchlistData);
      setSavedProperties(watchlistData.map((item) => item.id));

      // Load market insights for trending suburbs
      await propertyIntelligenceService.getMarketInsights(
        "Australia",
        ["trends", "forecasts"],
        10
      );

      // Set mock market insights (replace with real API call when available)
      setMarketInsights({
        nationalGrowth: 5.2,
        interestRate: 4.25,
        averageSettlement: 28,
        hotSuburbs: ["Teneriffe", "Paddington", "Newstead"],
        marketTrend: "rising",
        confidenceIndex: 78,
      });

      // Load initial property search (default search)
      await searchProperties();
    } catch (error) {
      console.error("Failed to load initial data:", error);
      setError("Failed to load property data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const searchProperties = async () => {
    if (!searchQuery && !hasActiveFilters()) {
      // Load sample properties for initial view
      await loadSampleProperties();
      return;
    }

    setIsSearching(true);
    setError(null);

    try {
      const searchRequest: PropertySearchRequest = {
        query: searchQuery,
        filters: {
          property_types: filters.propertyType ? [filters.propertyType] : [],
          min_bedrooms: filters.bedrooms
            ? parseInt(filters.bedrooms)
            : undefined,
          min_price: getPriceRangeMin(filters.priceRange),
          max_price: getPriceRangeMax(filters.priceRange),
          suburbs: [],
          states: [],
          features_required: [],
        },
        location: searchQuery,
        radius_km: 10.0,
        limit: 20,
        sort_by: "relevance",
        include_off_market: false,
        include_historical: false,
      };

      const response = await propertyIntelligenceService.searchProperties(
        searchRequest
      );
      const transformedProperties = transformPropertyListings(
        response.properties
      );
      setProperties(transformedProperties);
    } catch (error) {
      console.error("Property search failed:", error);
      setError("Search failed. Please try again.");
      // Fallback to sample properties
      await loadSampleProperties();
    } finally {
      setIsSearching(false);
    }
  };

  const loadSampleProperties = async () => {
    try {
      // Search for properties in major Australian cities
      const locations = ["Melbourne, VIC", "Sydney, NSW", "Brisbane, QLD"];
      let allProperties: PropertyDisplay[] = [];

      for (const location of locations) {
        try {
          const response =
            await propertyIntelligenceService.searchPropertiesAdvanced({
              location,
              limit: 5,
            });
          const transformed = transformPropertyListings(response.properties);
          allProperties = [...allProperties, ...transformed];
        } catch (error) {
          console.error(`Failed to load properties for ${location}:`, error);
        }
      }

      setProperties(allProperties.slice(0, 12)); // Limit to 12 properties
    } catch (error) {
      console.error("Failed to load sample properties:", error);
      // Set empty array if all fails
      setProperties([]);
    }
  };

  const transformPropertyListings = (
    listings: PropertyListing[]
  ): PropertyDisplay[] => {
    return listings.map((listing) => ({
      id: listing.id,
      address: listing.address,
      suburb: listing.address.split(",")[1]?.trim(),
      state: listing.address.split(",")[2]?.trim(),
      propertyType: listing.property_type,
      bedrooms: listing.bedrooms,
      bathrooms: listing.bathrooms,
      carSpaces: listing.carspaces,
      currentValue: listing.price,
      confidence: Math.round(listing.market_score * 10), // Convert 0-10 to percentage-like
      riskScore: Math.max(1, 10 - listing.investment_score), // Inverse of investment score
      investmentScore: listing.investment_score,
      growthRate: Math.random() * 8 + 2, // Mock data - replace with real calculation
      yield: ((listing.estimated_rental * 52) / listing.price) * 100,
      isSaved: savedProperties.includes(listing.id),
      lastUpdated: listing.listing_date,
      priceChange: Math.random() * 20000 - 10000, // Mock data
      daysOnMarket: Math.floor(Math.random() * 60) + 7,
      schoolScore: Math.random() * 3 + 7, // Mock data 7-10
      amenityScore: Math.random() * 3 + 7,
      transportScore: Math.random() * 3 + 7,
      environmentalRisk: Math.random() > 0.7 ? "Medium" : "Low",
      estimated_rental: listing.estimated_rental,
    }));
  };

  const hasActiveFilters = (): boolean => {
    return Object.values(filters).some((value) => value !== "");
  };

  const getPriceRangeMin = (range: string): number | undefined => {
    switch (range) {
      case "500k-1m":
        return 500000;
      case "1m-2m":
        return 1000000;
      case "2m+":
        return 2000000;
      default:
        return undefined;
    }
  };

  const getPriceRangeMax = (range: string): number | undefined => {
    switch (range) {
      case "0-500k":
        return 500000;
      case "500k-1m":
        return 1000000;
      case "1m-2m":
        return 2000000;
      default:
        return undefined;
    }
  };

  const toggleSaveProperty = async (propertyId: string) => {
    try {
      const property = properties.find((p) => p.id === propertyId);
      if (!property) return;

      if (savedProperties.includes(propertyId)) {
        // Remove from watchlist
        const watchlistItem = watchlist.find(
          (w) => w.property.address.full_address === property.address
        );
        if (watchlistItem) {
          await propertyIntelligenceService.removeFromWatchlist(
            watchlistItem.id
          );
        }
        setSavedProperties((prev) => prev.filter((id) => id !== propertyId));
      } else {
        // Add to watchlist
        await propertyIntelligenceService.addToWatchlist({
          address: property.address,
          notes: "Added from Property Intelligence search",
          tags: ["search_result"],
          alert_preferences: {},
        });
        setSavedProperties((prev) => [...prev, propertyId]);
      }

      // Update property in local state
      setProperties((prev) =>
        prev.map((p) =>
          p.id === propertyId ? { ...p, isSaved: !p.isSaved } : p
        )
      );
    } catch (error) {
      console.error("Failed to toggle property save:", error);
      setError("Failed to update saved properties. Please try again.");
    }
  };

  const handleSearch = () => {
    searchProperties();
  };

  const handleFilterChange = (filterName: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [filterName]: value,
    }));
  };

  const applyFilters = () => {
    searchProperties();
    setShowFilters(false);
  };

  const getRiskColor = (score: number) => {
    if (score < 3) return "text-success-600";
    if (score < 6) return "text-warning-600";
    return "text-danger-600";
  };

  const getRiskLabel = (score: number) => {
    if (score < 3) return "Low Risk";
    if (score < 6) return "Medium Risk";
    return "High Risk";
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header with Search */}
      <Card variant="premium" gradient className="overflow-hidden">
        <CardContent padding="xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
              <div>
                <h1 className="text-4xl font-heading font-bold text-neutral-900 mb-2">
                  Property Intelligence
                </h1>
                <p className="text-lg text-neutral-600 max-w-2xl">
                  Discover, analyze and compare properties with AI-powered
                  insights for the Australian market
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge
                  status="verified"
                  label="Australian Market Data"
                  variant="outline"
                />
                <StatusBadge
                  status="premium"
                  label="Real-time Updates"
                  variant="outline"
                />
              </div>
            </div>

            {/* Enhanced Search Bar */}
            <div className="relative max-w-3xl">
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-neutral-400 w-5 h-5" />
                  <input
                    type="text"
                    placeholder="Search by address, suburb, or postcode..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-12 pr-4 py-4 bg-white/90 backdrop-blur border border-neutral-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-200 text-lg"
                  />
                </div>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => setShowFilters(!showFilters)}
                  className="px-6"
                >
                  <Filter className="w-5 h-5 mr-2" />
                  Filters
                </Button>
                <Button
                  variant="primary"
                  size="lg"
                  className="px-8"
                  onClick={handleSearch}
                  disabled={isSearching}
                >
                  {isSearching ? "Searching..." : "Search Properties"}
                </Button>
              </div>
            </div>
          </motion.div>
        </CardContent>
      </Card>

      {/* Market Intelligence Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card variant="elevated">
          <CardHeader padding="lg">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-primary-600" />
                Australian Market Intelligence
              </CardTitle>
              {marketInsights && (
                <StatusBadge
                  status={
                    marketInsights.marketTrend === "rising"
                      ? "success"
                      : "warning"
                  }
                  label={`Market ${marketInsights.marketTrend}`}
                  variant="dot"
                />
              )}
            </div>
          </CardHeader>
          <CardContent padding="lg">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <TrendingUp className="w-8 h-8 text-primary-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-primary-600 mb-1">
                  {marketInsights ? `+${marketInsights.nationalGrowth}%` : "--"}
                </div>
                <div className="font-medium text-neutral-700">
                  National Growth
                </div>
                <div className="text-sm text-neutral-500">12 months</div>
              </div>

              <div className="text-center">
                <div className="w-16 h-16 bg-warning-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Calculator className="w-8 h-8 text-warning-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-warning-600 mb-1">
                  {marketInsights ? `${marketInsights.interestRate}%` : "--"}
                </div>
                <div className="font-medium text-neutral-700">Cash Rate</div>
                <div className="text-sm text-neutral-500">RBA Current</div>
              </div>

              <div className="text-center">
                <div className="w-16 h-16 bg-success-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Calendar className="w-8 h-8 text-success-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-success-600 mb-1">
                  {marketInsights ? marketInsights.averageSettlement : "--"}
                </div>
                <div className="font-medium text-neutral-700">
                  Days Settlement
                </div>
                <div className="text-sm text-neutral-500">Average</div>
              </div>

              <div className="text-center">
                <div className="w-16 h-16 bg-trust-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <BarChart3 className="w-8 h-8 text-trust-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-trust-600 mb-1">
                  {marketInsights ? marketInsights.confidenceIndex : "--"}
                </div>
                <div className="font-medium text-neutral-700">
                  Confidence Index
                </div>
                <div className="text-sm text-neutral-500">Market Sentiment</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Filters Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <Card variant="elevated">
              <CardContent padding="lg">
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Property Type
                    </label>
                    <select
                      className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                      value={filters.propertyType}
                      onChange={(e) =>
                        handleFilterChange("propertyType", e.target.value)
                      }
                    >
                      <option value="">Any</option>
                      <option value="House">House</option>
                      <option value="Apartment">Apartment</option>
                      <option value="Townhouse">Townhouse</option>
                      <option value="Unit">Unit</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Bedrooms
                    </label>
                    <select
                      className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                      value={filters.bedrooms}
                      onChange={(e) =>
                        handleFilterChange("bedrooms", e.target.value)
                      }
                    >
                      <option value="">Any</option>
                      <option value="1">1+</option>
                      <option value="2">2+</option>
                      <option value="3">3+</option>
                      <option value="4">4+</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Price Range
                    </label>
                    <select
                      className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                      value={filters.priceRange}
                      onChange={(e) =>
                        handleFilterChange("priceRange", e.target.value)
                      }
                    >
                      <option value="">Any</option>
                      <option value="0-500k">Under $500K</option>
                      <option value="500k-1m">$500K - $1M</option>
                      <option value="1m-2m">$1M - $2M</option>
                      <option value="2m+">$2M+</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Risk Level
                    </label>
                    <select
                      className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                      value={filters.riskLevel}
                      onChange={(e) =>
                        handleFilterChange("riskLevel", e.target.value)
                      }
                    >
                      <option value="">Any</option>
                      <option value="low">Low Risk (1-3)</option>
                      <option value="medium">Medium Risk (4-6)</option>
                      <option value="high">High Risk (7-10)</option>
                    </select>
                  </div>

                  <div className="flex items-end">
                    <Button variant="primary" fullWidth onClick={applyFilters}>
                      Apply Filters
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="flex flex-wrap gap-4 mb-6">
          <Button variant="outline" className="flex items-center gap-2">
            <Bookmark className="w-4 h-4" />
            Saved Properties ({savedProperties.length})
          </Button>
          <Button variant="outline" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Compare Properties
          </Button>
          <Button variant="outline" className="flex items-center gap-2">
            <Bell className="w-4 h-4" />
            Price Alerts
          </Button>
          <Button variant="outline" className="flex items-center gap-2">
            <Calculator className="w-4 h-4" />
            Affordability Calculator
          </Button>
        </div>
      </motion.div>

      {/* Property Results */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card variant="elevated">
          <CardHeader padding="lg">
            <div className="flex items-center justify-between">
              <CardTitle>Property Search Results</CardTitle>
              <div className="flex items-center gap-3">
                <span className="text-sm text-neutral-500">
                  {properties.length} properties found
                </span>
                <div className="flex rounded-lg border border-neutral-200">
                  <button
                    onClick={() => setSelectedView("grid")}
                    className={cn(
                      "px-3 py-1 text-sm rounded-l-lg transition-colors",
                      selectedView === "grid"
                        ? "bg-primary-100 text-primary-600"
                        : "text-neutral-500 hover:text-neutral-700"
                    )}
                  >
                    Grid
                  </button>
                  <button
                    onClick={() => setSelectedView("list")}
                    className={cn(
                      "px-3 py-1 text-sm rounded-r-lg transition-colors",
                      selectedView === "list"
                        ? "bg-primary-100 text-primary-600"
                        : "text-neutral-500 hover:text-neutral-700"
                    )}
                  >
                    List
                  </button>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent padding="lg">
            {/* Error Display */}
            {error && (
              <div className="mb-4 p-4 bg-danger-50 border border-danger-200 rounded-lg">
                <div className="flex items-center gap-2 text-danger-700">
                  <AlertTriangle className="w-5 h-5" />
                  <span className="font-medium">{error}</span>
                </div>
              </div>
            )}

            {/* Loading State */}
            {isLoading && (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                <p className="text-neutral-600">
                  Loading property intelligence...
                </p>
              </div>
            )}

            {/* Empty State */}
            {!isLoading && properties.length === 0 && !error && (
              <div className="text-center py-8">
                <Building className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-neutral-700 mb-2">
                  No Properties Found
                </h3>
                <p className="text-neutral-500 mb-4">
                  Try adjusting your search criteria or filters.
                </p>
                <Button
                  variant="primary"
                  onClick={() => {
                    setSearchQuery("");
                    setFilters({
                      propertyType: "",
                      bedrooms: "",
                      priceRange: "",
                      riskLevel: "",
                    });
                    loadSampleProperties();
                  }}
                >
                  Load Sample Properties
                </Button>
              </div>
            )}

            {/* Properties Grid/List */}
            {!isLoading && properties.length > 0 && (
              <div
                className={cn(
                  "gap-6",
                  selectedView === "grid"
                    ? "grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3"
                    : "space-y-4"
                )}
              >
                {properties.map((property, index) => (
                  <motion.div
                    key={property.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <Card
                      variant="outlined"
                      interactive
                      className="group hover:shadow-xl transition-all duration-300"
                    >
                      <CardContent padding="lg">
                        {/* Property Header */}
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Building className="w-4 h-4 text-neutral-400" />
                              <span className="text-sm font-medium text-neutral-600">
                                {property.propertyType}
                              </span>
                              <StatusBadge
                                status={
                                  property.environmentalRisk === "Low"
                                    ? "success"
                                    : "warning"
                                }
                                label={`${property.environmentalRisk} Env Risk`}
                                size="sm"
                                variant="dot"
                              />
                            </div>
                            <h3 className="font-semibold text-neutral-900 group-hover:text-primary-600 transition-colors">
                              {property.address}
                            </h3>
                            <div className="flex items-center gap-4 mt-2 text-sm text-neutral-600">
                              <span>{property.bedrooms} bed</span>
                              <span>{property.bathrooms} bath</span>
                              <span>{property.carSpaces} car</span>
                            </div>
                          </div>
                          <button
                            onClick={() => toggleSaveProperty(property.id)}
                            className="p-2 hover:bg-neutral-100 rounded-lg transition-colors"
                          >
                            {savedProperties.includes(property.id) ? (
                              <BookmarkCheck className="w-5 h-5 text-primary-600" />
                            ) : (
                              <Bookmark className="w-5 h-5 text-neutral-400" />
                            )}
                          </button>
                        </div>

                        {/* Property Value & Metrics */}
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-2xl font-heading font-bold text-neutral-900">
                                ${property.currentValue.toLocaleString()}
                              </div>
                              <div className="flex items-center gap-2 text-sm">
                                <span className="text-neutral-500">
                                  {property.confidence}% confidence
                                </span>
                                <span
                                  className={cn(
                                    "flex items-center gap-1",
                                    (property.priceChange ?? 0) > 0
                                      ? "text-success-600"
                                      : "text-danger-600"
                                  )}
                                >
                                  <TrendingUp className="w-3 h-3" />$
                                  {Math.abs(
                                    property.priceChange ?? 0
                                  ).toLocaleString()}
                                </span>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-2 mb-1">
                                <Star className="w-4 h-4 text-warning-500 fill-current" />
                                <span className="font-semibold text-neutral-900">
                                  {property.investmentScore}/10
                                </span>
                              </div>
                              <div className="text-sm text-neutral-500">
                                Investment Score
                              </div>
                            </div>
                          </div>

                          {/* Risk Assessment */}
                          <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                            <div className="flex items-center gap-2">
                              <ShieldCheck
                                className={cn(
                                  "w-4 h-4",
                                  getRiskColor(property.riskScore ?? 0)
                                )}
                              />
                              <span className="text-sm font-medium text-neutral-700">
                                Risk Assessment
                              </span>
                            </div>
                            <div className="text-right">
                              <div
                                className={cn(
                                  "font-semibold",
                                  getRiskColor(property.riskScore ?? 0)
                                )}
                              >
                                {property.riskScore ?? 0}/10
                              </div>
                              <div className="text-xs text-neutral-500">
                                {getRiskLabel(property.riskScore ?? 0)}
                              </div>
                            </div>
                          </div>

                          {/* Key Metrics */}
                          <div className="grid grid-cols-3 gap-4">
                            <div className="text-center">
                              <div className="font-semibold text-neutral-900">
                                {property.growthRate}%
                              </div>
                              <div className="text-xs text-neutral-500">
                                Growth
                              </div>
                            </div>
                            <div className="text-center">
                              <div className="font-semibold text-neutral-900">
                                {property.yield}%
                              </div>
                              <div className="text-xs text-neutral-500">
                                Yield
                              </div>
                            </div>
                            <div className="text-center">
                              <div className="font-semibold text-neutral-900">
                                {property.daysOnMarket}
                              </div>
                              <div className="text-xs text-neutral-500">
                                Days
                              </div>
                            </div>
                          </div>

                          {/* Score Indicators */}
                          <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-neutral-600">
                                School Score
                              </span>
                              <span className="font-medium">
                                {property.schoolScore}/10
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-neutral-600">
                                Amenities
                              </span>
                              <span className="font-medium">
                                {property.amenityScore}/10
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-neutral-600">
                                Transport
                              </span>
                              <span className="font-medium">
                                {property.transportScore}/10
                              </span>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="flex gap-2 pt-4 border-t border-neutral-100">
                            <Button variant="primary" size="sm" fullWidth>
                              View Details
                            </Button>
                            <Button variant="outline" size="sm">
                              <BarChart3 className="w-4 h-4" />
                            </Button>
                            <Button variant="outline" size="sm">
                              <Calculator className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Hot Suburbs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card variant="glass">
          <CardHeader padding="lg">
            <CardTitle className="flex items-center gap-3">
              <TrendingUp className="w-6 h-6 text-primary-600" />
              Hot Suburbs This Month
            </CardTitle>
          </CardHeader>
          <CardContent padding="lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {marketInsights && marketInsights.hotSuburbs.length > 0 ? (
                marketInsights.hotSuburbs.map((suburb, index) => (
                  <div
                    key={suburb}
                    className="flex items-center gap-3 p-4 bg-white/60 rounded-xl"
                  >
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-primary-600 font-bold text-sm">
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-medium text-neutral-900">
                        {suburb}
                      </div>
                      <div className="text-sm text-neutral-500">
                        High Growth Area
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-3 text-center py-4 text-neutral-500">
                  Loading market insights...
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default PropertyIntelligencePage;

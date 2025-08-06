import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  MapPin,
  TrendingUp,
  Home,
  DollarSign,
  AlertTriangle,
  Bookmark,
  BookmarkCheck,
  Filter,
  ArrowRight,
  BarChart3,
  Calculator,
  Compare,
  Bell,
  Star,
  Eye,
  Heart,
  Building,
  Coins,
  ShieldCheck,
  Calendar,
  ChevronDown,
} from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import StatusBadge from "@/components/ui/StatusBadge";
import { cn } from "@/utils";

// Mock data for demonstration
const mockProperties = [
  {
    id: "1",
    address: "45 Collins Street, Melbourne VIC 3000",
    suburb: "Melbourne",
    state: "VIC",
    propertyType: "Apartment",
    bedrooms: 2,
    bathrooms: 2,
    carSpaces: 1,
    currentValue: 850000,
    confidence: 92,
    riskScore: 2.8,
    investmentScore: 8.2,
    growthRate: 5.2,
    yield: 4.1,
    isSaved: false,
    lastUpdated: "2024-01-15T10:30:00Z",
    priceChange: 12000,
    daysOnMarket: 21,
    schoolScore: 9.2,
    amenityScore: 8.8,
    transportScore: 9.5,
    environmentalRisk: "Low",
  },
  {
    id: "2",
    address: "123 George Street, Sydney NSW 2000",
    suburb: "Sydney",
    state: "NSW",
    propertyType: "House",
    bedrooms: 3,
    bathrooms: 2,
    carSpaces: 2,
    currentValue: 1200000,
    confidence: 88,
    riskScore: 4.5,
    investmentScore: 7.8,
    growthRate: 3.8,
    yield: 3.2,
    isSaved: true,
    lastUpdated: "2024-01-14T15:45:00Z",
    priceChange: -5000,
    daysOnMarket: 45,
    schoolScore: 8.7,
    amenityScore: 9.1,
    transportScore: 8.9,
    environmentalRisk: "Medium",
  },
  {
    id: "3",
    address: "67 Queen Street, Brisbane QLD 4000",
    suburb: "Brisbane",
    state: "QLD",
    propertyType: "Townhouse",
    bedrooms: 3,
    bathrooms: 2,
    carSpaces: 2,
    currentValue: 720000,
    confidence: 85,
    riskScore: 3.2,
    investmentScore: 8.5,
    growthRate: 6.1,
    yield: 4.8,
    isSaved: true,
    lastUpdated: "2024-01-13T09:15:00Z",
    priceChange: 18000,
    daysOnMarket: 12,
    schoolScore: 8.5,
    amenityScore: 7.9,
    transportScore: 8.2,
    environmentalRisk: "Low",
  },
];

const mockMarketInsights = {
  nationalGrowth: 5.2,
  interestRate: 4.25,
  averageSettlement: 28,
  hotSuburbs: ["Teneriffe, QLD", "Richmond, VIC", "Paddington, NSW"],
  marketTrend: "rising",
  confidenceIndex: 78,
};

const PropertyIntelligencePage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedView, setSelectedView] = useState<"grid" | "list">("grid");
  const [selectedProperty, setSelectedProperty] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [savedProperties, setSavedProperties] = useState<string[]>(
    mockProperties.filter(p => p.isSaved).map(p => p.id)
  );

  const toggleSaveProperty = (propertyId: string) => {
    setSavedProperties(prev => 
      prev.includes(propertyId) 
        ? prev.filter(id => id !== propertyId)
        : [...prev, propertyId]
    );
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
                  Discover, analyze and compare properties with AI-powered insights for the Australian market
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
                <Button variant="primary" size="lg" className="px-8">
                  Search Properties
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
              <StatusBadge
                status={mockMarketInsights.marketTrend === "rising" ? "success" : "warning"}
                label={`Market ${mockMarketInsights.marketTrend}`}
                variant="dot"
              />
            </div>
          </CardHeader>
          <CardContent padding="lg">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <TrendingUp className="w-8 h-8 text-primary-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-primary-600 mb-1">
                  +{mockMarketInsights.nationalGrowth}%
                </div>
                <div className="font-medium text-neutral-700">National Growth</div>
                <div className="text-sm text-neutral-500">12 months</div>
              </div>
              
              <div className="text-center">
                <div className="w-16 h-16 bg-warning-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Calculator className="w-8 h-8 text-warning-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-warning-600 mb-1">
                  {mockMarketInsights.interestRate}%
                </div>
                <div className="font-medium text-neutral-700">Cash Rate</div>
                <div className="text-sm text-neutral-500">RBA Current</div>
              </div>
              
              <div className="text-center">
                <div className="w-16 h-16 bg-success-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Calendar className="w-8 h-8 text-success-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-success-600 mb-1">
                  {mockMarketInsights.averageSettlement}
                </div>
                <div className="font-medium text-neutral-700">Days Settlement</div>
                <div className="text-sm text-neutral-500">Average</div>
              </div>
              
              <div className="text-center">
                <div className="w-16 h-16 bg-trust-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <BarChart3 className="w-8 h-8 text-trust-600" />
                </div>
                <div className="text-3xl font-heading font-bold text-trust-600 mb-1">
                  {mockMarketInsights.confidenceIndex}
                </div>
                <div className="font-medium text-neutral-700">Confidence Index</div>
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
                    <select className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500">
                      <option value="">Any</option>
                      <option value="house">House</option>
                      <option value="apartment">Apartment</option>
                      <option value="townhouse">Townhouse</option>
                      <option value="unit">Unit</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Bedrooms
                    </label>
                    <select className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500">
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
                    <select className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500">
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
                    <select className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500">
                      <option value="">Any</option>
                      <option value="low">Low Risk (1-3)</option>
                      <option value="medium">Medium Risk (4-6)</option>
                      <option value="high">High Risk (7-10)</option>
                    </select>
                  </div>
                  
                  <div className="flex items-end">
                    <Button variant="primary" fullWidth>
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
            <Compare className="w-4 h-4" />
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
                  {mockProperties.length} properties found
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
            <div className={cn(
              "gap-6",
              selectedView === "grid" 
                ? "grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3" 
                : "space-y-4"
            )}>
              {mockProperties.map((property, index) => (
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
                              status={property.environmentalRisk === "Low" ? "success" : "warning"}
                              label={`${property.environmentalRisk} Env Risk`}
                              size="xs"
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
                              <span className={cn(
                                "flex items-center gap-1",
                                property.priceChange > 0 ? "text-success-600" : "text-danger-600"
                              )}>
                                <TrendingUp className="w-3 h-3" />
                                ${Math.abs(property.priceChange).toLocaleString()}
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
                            <ShieldCheck className={cn("w-4 h-4", getRiskColor(property.riskScore))} />
                            <span className="text-sm font-medium text-neutral-700">
                              Risk Assessment
                            </span>
                          </div>
                          <div className="text-right">
                            <div className={cn("font-semibold", getRiskColor(property.riskScore))}>
                              {property.riskScore}/10
                            </div>
                            <div className="text-xs text-neutral-500">
                              {getRiskLabel(property.riskScore)}
                            </div>
                          </div>
                        </div>

                        {/* Key Metrics */}
                        <div className="grid grid-cols-3 gap-4">
                          <div className="text-center">
                            <div className="font-semibold text-neutral-900">
                              {property.growthRate}%
                            </div>
                            <div className="text-xs text-neutral-500">Growth</div>
                          </div>
                          <div className="text-center">
                            <div className="font-semibold text-neutral-900">
                              {property.yield}%
                            </div>
                            <div className="text-xs text-neutral-500">Yield</div>
                          </div>
                          <div className="text-center">
                            <div className="font-semibold text-neutral-900">
                              {property.daysOnMarket}
                            </div>
                            <div className="text-xs text-neutral-500">Days</div>
                          </div>
                        </div>

                        {/* Score Indicators */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-neutral-600">School Score</span>
                            <span className="font-medium">{property.schoolScore}/10</span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-neutral-600">Amenities</span>
                            <span className="font-medium">{property.amenityScore}/10</span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-neutral-600">Transport</span>
                            <span className="font-medium">{property.transportScore}/10</span>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-2 pt-4 border-t border-neutral-100">
                          <Button variant="primary" size="sm" fullWidth>
                            View Details
                          </Button>
                          <Button variant="outline" size="sm">
                            <Compare className="w-4 h-4" />
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
              {mockMarketInsights.hotSuburbs.map((suburb, index) => (
                <div key={suburb} className="flex items-center gap-3 p-4 bg-white/60 rounded-xl">
                  <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-primary-600 font-bold text-sm">
                    {index + 1}
                  </div>
                  <div>
                    <div className="font-medium text-neutral-900">{suburb}</div>
                    <div className="text-sm text-neutral-500">High Growth Area</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default PropertyIntelligencePage;
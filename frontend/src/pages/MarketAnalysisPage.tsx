import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart,
  MapPin,
  Calendar,
  DollarSign,
  Home,
  AlertCircle,
  Zap,
  Target,
  ArrowRight,
  Filter,
  Download,
} from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import StatusBadge from "@/components/ui/StatusBadge";
import { cn } from "@/utils";

// Mock data for market analysis
const mockMarketData = {
  nationalStats: {
    medianPrice: 750000,
    priceGrowth: 5.2,
    salesVolume: 42850,
    daysOnMarket: 32,
    auctionClearance: 68.5,
    rentalYield: 4.1,
  },
  stateComparison: [
    { state: "NSW", medianPrice: 950000, growth: 4.8, volume: 15200, trend: "up" },
    { state: "VIC", medianPrice: 720000, growth: 6.1, volume: 12500, trend: "up" },
    { state: "QLD", medianPrice: 650000, growth: 7.2, volume: 8900, trend: "up" },
    { state: "WA", medianPrice: 580000, growth: 3.9, volume: 4200, trend: "neutral" },
    { state: "SA", medianPrice: 520000, growth: 5.8, volume: 2100, trend: "up" },
    { state: "TAS", medianPrice: 480000, growth: 2.1, volume: 850, trend: "down" },
    { state: "ACT", medianPrice: 820000, growth: 4.2, volume: 650, trend: "neutral" },
    { state: "NT", medianPrice: 450000, growth: 1.8, volume: 320, trend: "down" },
  ],
  hotSuburbs: [
    { name: "Teneriffe, QLD", growth: 15.2, medianPrice: 850000, riskLevel: "medium" },
    { name: "Richmond, VIC", growth: 12.8, medianPrice: 920000, riskLevel: "low" },
    { name: "Paddington, NSW", growth: 11.5, medianPrice: 1250000, riskLevel: "low" },
    { name: "Fremantle, WA", growth: 10.9, medianPrice: 680000, riskLevel: "medium" },
    { name: "Norwood, SA", growth: 9.8, medianPrice: 780000, riskLevel: "low" },
  ],
  marketPredictions: {
    sixMonth: { trend: "rising", confidence: 78, priceChange: 2.8 },
    oneYear: { trend: "stable", confidence: 65, priceChange: 4.2 },
    twoYear: { trend: "rising", confidence: 52, priceChange: 8.5 },
  },
  riskFactors: [
    { factor: "Interest Rate Changes", impact: "High", probability: 85 },
    { factor: "Supply Shortage", impact: "Medium", probability: 72 },
    { factor: "Economic Downturn", impact: "High", probability: 35 },
    { factor: "Regulatory Changes", impact: "Medium", probability: 45 },
  ],
};

const MarketAnalysisPage: React.FC = () => {
  const [selectedTimeframe, setSelectedTimeframe] = useState<"3M" | "6M" | "1Y" | "2Y">("1Y");
  const [selectedRegion, setSelectedRegion] = useState<"national" | "state" | "suburb">("national");

  const getTrendIcon = (trend: string, size = "w-4 h-4") => {
    switch (trend) {
      case "up":
        return <TrendingUp className={cn(size, "text-success-600")} />;
      case "down":
        return <TrendingDown className={cn(size, "text-danger-600")} />;
      default:
        return <Target className={cn(size, "text-warning-600")} />;
    }
  };

  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case "low":
        return "text-success-600 bg-success-100";
      case "medium":
        return "text-warning-600 bg-warning-100";
      case "high":
        return "text-danger-600 bg-danger-100";
      default:
        return "text-neutral-600 bg-neutral-100";
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
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
                  Market Analysis
                </h1>
                <p className="text-lg text-neutral-600 max-w-2xl">
                  Comprehensive market insights and predictions for the Australian property market
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge
                  status="verified"
                  label="Real-time Data"
                  variant="outline"
                />
                <StatusBadge
                  status="premium"
                  label="AI Predictions"
                  variant="outline"
                />
              </div>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex rounded-lg border border-neutral-200 bg-white/50">
                {(["3M", "6M", "1Y", "2Y"] as const).map((timeframe) => (
                  <button
                    key={timeframe}
                    onClick={() => setSelectedTimeframe(timeframe)}
                    className={cn(
                      "px-4 py-2 text-sm font-medium transition-colors first:rounded-l-lg last:rounded-r-lg",
                      selectedTimeframe === timeframe
                        ? "bg-primary-600 text-white"
                        : "text-neutral-600 hover:text-neutral-900"
                    )}
                  >
                    {timeframe}
                  </button>
                ))}
              </div>

              <div className="flex rounded-lg border border-neutral-200 bg-white/50">
                {(["national", "state", "suburb"] as const).map((region) => (
                  <button
                    key={region}
                    onClick={() => setSelectedRegion(region)}
                    className={cn(
                      "px-4 py-2 text-sm font-medium capitalize transition-colors first:rounded-l-lg last:rounded-r-lg",
                      selectedRegion === region
                        ? "bg-primary-600 text-white"
                        : "text-neutral-600 hover:text-neutral-900"
                    )}
                  >
                    {region}
                  </button>
                ))}
              </div>

              <Button variant="outline" size="sm">
                <Filter className="w-4 h-4 mr-2" />
                Advanced Filters
              </Button>

              <Button variant="primary" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Export Report
              </Button>
            </div>
          </motion.div>
        </CardContent>
      </Card>

      {/* National Market Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card variant="elevated">
          <CardHeader padding="lg">
            <CardTitle className="flex items-center gap-3">
              <BarChart3 className="w-6 h-6 text-primary-600" />
              National Market Overview
            </CardTitle>
          </CardHeader>
          <CardContent padding="lg">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <DollarSign className="w-6 h-6 text-primary-600" />
                </div>
                <div className="text-2xl font-heading font-bold text-neutral-900">
                  ${(mockMarketData.nationalStats.medianPrice / 1000).toFixed(0)}K
                </div>
                <div className="text-sm text-neutral-500">Median Price</div>
              </div>

              <div className="text-center">
                <div className="w-12 h-12 bg-success-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <TrendingUp className="w-6 h-6 text-success-600" />
                </div>
                <div className="text-2xl font-heading font-bold text-success-600">
                  +{mockMarketData.nationalStats.priceGrowth}%
                </div>
                <div className="text-sm text-neutral-500">Price Growth</div>
              </div>

              <div className="text-center">
                <div className="w-12 h-12 bg-trust-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Home className="w-6 h-6 text-trust-600" />
                </div>
                <div className="text-2xl font-heading font-bold text-neutral-900">
                  {(mockMarketData.nationalStats.salesVolume / 1000).toFixed(1)}K
                </div>
                <div className="text-sm text-neutral-500">Sales Volume</div>
              </div>

              <div className="text-center">
                <div className="w-12 h-12 bg-warning-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Calendar className="w-6 h-6 text-warning-600" />
                </div>
                <div className="text-2xl font-heading font-bold text-neutral-900">
                  {mockMarketData.nationalStats.daysOnMarket}
                </div>
                <div className="text-sm text-neutral-500">Days on Market</div>
              </div>

              <div className="text-center">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Target className="w-6 h-6 text-purple-600" />
                </div>
                <div className="text-2xl font-heading font-bold text-neutral-900">
                  {mockMarketData.nationalStats.auctionClearance}%
                </div>
                <div className="text-sm text-neutral-500">Auction Clearance</div>
              </div>

              <div className="text-center">
                <div className="w-12 h-12 bg-cyan-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <PieChart className="w-6 h-6 text-cyan-600" />
                </div>
                <div className="text-2xl font-heading font-bold text-neutral-900">
                  {mockMarketData.nationalStats.rentalYield}%
                </div>
                <div className="text-sm text-neutral-500">Rental Yield</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* State Comparison */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card variant="elevated" className="h-fit">
            <CardHeader padding="lg">
              <CardTitle className="flex items-center gap-3">
                <MapPin className="w-6 h-6 text-primary-600" />
                State Market Comparison
              </CardTitle>
            </CardHeader>
            <CardContent padding="lg">
              <div className="space-y-4">
                {mockMarketData.stateComparison.map((state) => (
                  <div key={state.state} className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                        <span className="font-bold text-primary-600 text-sm">
                          {state.state}
                        </span>
                      </div>
                      <div>
                        <div className="font-semibold text-neutral-900">
                          ${(state.medianPrice / 1000).toFixed(0)}K
                        </div>
                        <div className="text-sm text-neutral-500">
                          {(state.volume / 1000).toFixed(1)}K sales
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className={cn(
                          "font-semibold",
                          state.growth > 5 ? "text-success-600" : 
                          state.growth > 3 ? "text-warning-600" : "text-danger-600"
                        )}>
                          +{state.growth}%
                        </div>
                        <div className="text-sm text-neutral-500">Growth</div>
                      </div>
                      {getTrendIcon(state.trend, "w-5 h-5")}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Market Predictions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card variant="elevated" className="h-fit">
            <CardHeader padding="lg">
              <CardTitle className="flex items-center gap-3">
                <Zap className="w-6 h-6 text-primary-600" />
                AI Market Predictions
              </CardTitle>
            </CardHeader>
            <CardContent padding="lg">
              <div className="space-y-6">
                <div className="p-4 bg-gradient-to-r from-primary-50 to-trust-50 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-lg font-semibold text-neutral-900">
                      6 Month Outlook
                    </div>
                    <StatusBadge
                      status={mockMarketData.marketPredictions.sixMonth.trend === "rising" ? "success" : "warning"}
                      label={mockMarketData.marketPredictions.sixMonth.trend}
                      variant="dot"
                      size="sm"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-2xl font-bold text-primary-600">
                        +{mockMarketData.marketPredictions.sixMonth.priceChange}%
                      </div>
                      <div className="text-sm text-neutral-500">Expected Growth</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-semibold text-neutral-900">
                        {mockMarketData.marketPredictions.sixMonth.confidence}%
                      </div>
                      <div className="text-sm text-neutral-500">Confidence</div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-xl font-bold text-neutral-900">
                        +{mockMarketData.marketPredictions.oneYear.priceChange}%
                      </div>
                      <div className="text-sm text-neutral-500 mb-1">12 Months</div>
                      <div className="text-xs text-neutral-400">
                        {mockMarketData.marketPredictions.oneYear.confidence}% confidence
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-xl font-bold text-neutral-900">
                        +{mockMarketData.marketPredictions.twoYear.priceChange}%
                      </div>
                      <div className="text-sm text-neutral-500 mb-1">24 Months</div>
                      <div className="text-xs text-neutral-400">
                        {mockMarketData.marketPredictions.twoYear.confidence}% confidence
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Hot Suburbs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card variant="elevated">
          <CardHeader padding="lg">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-primary-600" />
                High Growth Suburbs
              </CardTitle>
              <Button variant="outline" size="sm">
                View All
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardHeader>
          <CardContent padding="lg">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {mockMarketData.hotSuburbs.map((suburb, index) => (
                <Card key={suburb.name} variant="outlined" interactive>
                  <CardContent padding="lg">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="font-semibold text-neutral-900 mb-1">
                          {suburb.name}
                        </div>
                        <div className="text-sm text-neutral-500">
                          ${(suburb.medianPrice / 1000).toFixed(0)}K median
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-bold text-success-600">
                          +{suburb.growth}%
                        </div>
                        <div className="text-xs text-neutral-500">Growth</div>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span className={cn(
                        "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
                        getRiskColor(suburb.riskLevel)
                      )}>
                        {suburb.riskLevel} Risk
                      </span>
                      <div className="text-sm font-medium text-primary-600">
                        Rank #{index + 1}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Risk Factors */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card variant="elevated">
          <CardHeader padding="lg">
            <CardTitle className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-warning-600" />
              Market Risk Factors
            </CardTitle>
          </CardHeader>
          <CardContent padding="lg">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {mockMarketData.riskFactors.map((risk) => (
                <div key={risk.factor} className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <AlertCircle className={cn(
                      "w-5 h-5",
                      risk.impact === "High" ? "text-danger-500" : "text-warning-500"
                    )} />
                    <div>
                      <div className="font-medium text-neutral-900">
                        {risk.factor}
                      </div>
                      <div className="text-sm text-neutral-500">
                        {risk.impact} Impact
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-neutral-900">
                      {risk.probability}%
                    </div>
                    <div className="text-xs text-neutral-500">Probability</div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-6 p-4 bg-gradient-to-r from-warning-50 to-danger-50 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-warning-600 mt-0.5" />
                <div>
                  <div className="font-medium text-neutral-900 mb-1">
                    Market Risk Assessment
                  </div>
                  <div className="text-sm text-neutral-600">
                    Current market conditions show moderate risk levels. Interest rate changes remain
                    the highest probability risk factor. Consider diversified investment strategies
                    and maintain cash reserves for opportunities.
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default MarketAnalysisPage;
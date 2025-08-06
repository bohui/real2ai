import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Calculator,
  DollarSign,
  TrendingUp,
  PieChart,
  Target,
  AlertTriangle,
  CheckCircle,
  Home,
  Percent,
  Calendar,
  ArrowRight,
  Info,
  Banknote,
  Building,
  CreditCard,
  Shield,
} from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import StatusBadge from "@/components/ui/StatusBadge";
import { cn } from "@/utils";

// Mock calculation data
const mockCalculations = {
  affordability: {
    maxLoanAmount: 800000,
    monthlyRepayment: 4200,
    depositRequired: 160000,
    totalPropertyBudget: 960000,
    serviceability: 85,
    lmiRequired: false,
  },
  roiProjections: {
    purchasePrice: 850000,
    weeklyRent: 650,
    annualRent: 33800,
    grossYield: 4.0,
    netYield: 2.8,
    fiveYearROI: 45.2,
    tenYearROI: 92.8,
    cashFlow: -180,
  },
  taxAnalysis: {
    annualDeductions: 12500,
    taxSavings: 4375,
    depreciation: 8200,
    maintenanceDeductions: 4300,
    cgTaxLiability: 28500,
    negativeGearingBenefit: 6200,
  },
  insuranceEstimates: {
    buildingInsurance: 1200,
    contentsInsurance: 800,
    publicLiabilityInsurance: 450,
    totalAnnual: 2450,
    monthlyPremium: 204,
  },
};

const FinancialAnalysisPage: React.FC = () => {
  const [activeCalculator, setActiveCalculator] = useState<"affordability" | "roi" | "tax" | "insurance">("affordability");
  const [propertyPrice, setPropertyPrice] = useState(850000);
  const [annualIncome, setAnnualIncome] = useState(120000);
  const [deposit, setDeposit] = useState(170000);
  const [interestRate, setInterestRate] = useState(6.5);

  const calculatorTabs = [
    { id: "affordability" as const, label: "Affordability", icon: Home },
    { id: "roi" as const, label: "ROI Analysis", icon: TrendingUp },
    { id: "tax" as const, label: "Tax Analysis", icon: Calculator },
    { id: "insurance" as const, label: "Insurance", icon: Shield },
  ];

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
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
                  Financial Analysis
                </h1>
                <p className="text-lg text-neutral-600 max-w-2xl">
                  Comprehensive financial tools for property investment analysis and planning
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge
                  status="verified"
                  label="Australian Tax Laws"
                  variant="outline"
                />
                <StatusBadge
                  status="premium"
                  label="Real-time Rates"
                  variant="outline"
                />
              </div>
            </div>

            {/* Calculator Tabs */}
            <div className="flex flex-wrap gap-2">
              {calculatorTabs.map((tab) => {
                const IconComponent = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveCalculator(tab.id)}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200",
                      activeCalculator === tab.id
                        ? "bg-white text-primary-600 shadow-soft"
                        : "text-neutral-600 hover:text-neutral-900 hover:bg-white/50"
                    )}
                  >
                    <IconComponent className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </motion.div>
        </CardContent>
      </Card>

      {/* Input Parameters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card variant="elevated">
          <CardHeader padding="lg">
            <CardTitle className="flex items-center gap-3">
              <Calculator className="w-6 h-6 text-primary-600" />
              Input Parameters
            </CardTitle>
          </CardHeader>
          <CardContent padding="lg">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Property Price
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                  <input
                    type="number"
                    value={propertyPrice}
                    onChange={(e) => setPropertyPrice(Number(e.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Annual Income
                </label>
                <div className="relative">
                  <Banknote className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                  <input
                    type="number"
                    value={annualIncome}
                    onChange={(e) => setAnnualIncome(Number(e.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Deposit Amount
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                  <input
                    type="number"
                    value={deposit}
                    onChange={(e) => setDeposit(Number(e.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Interest Rate
                </label>
                <div className="relative">
                  <Percent className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                  <input
                    type="number"
                    step="0.1"
                    value={interestRate}
                    onChange={(e) => setInterestRate(Number(e.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button variant="primary" className="px-8">
                Calculate Results
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Results Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {activeCalculator === "affordability" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Affordability Summary */}
            <Card variant="elevated">
              <CardHeader padding="lg">
                <CardTitle className="flex items-center gap-3">
                  <Home className="w-6 h-6 text-primary-600" />
                  Affordability Summary
                </CardTitle>
              </CardHeader>
              <CardContent padding="lg">
                <div className="space-y-6">
                  <div className="text-center p-6 bg-gradient-to-br from-primary-50 to-trust-50 rounded-xl">
                    <div className="text-3xl font-heading font-bold text-primary-600 mb-2">
                      {formatCurrency(mockCalculations.affordability.maxLoanAmount)}
                    </div>
                    <div className="text-lg font-medium text-neutral-700">Maximum Loan Amount</div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-neutral-50 rounded-lg">
                      <div className="text-xl font-bold text-neutral-900">
                        {formatCurrency(mockCalculations.affordability.monthlyRepayment)}
                      </div>
                      <div className="text-sm text-neutral-500">Monthly Repayment</div>
                    </div>
                    <div className="text-center p-4 bg-neutral-50 rounded-lg">
                      <div className="text-xl font-bold text-neutral-900">
                        {formatCurrency(mockCalculations.affordability.depositRequired)}
                      </div>
                      <div className="text-sm text-neutral-500">Deposit Required</div>
                    </div>
                  </div>

                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-neutral-700">Serviceability</span>
                      <span className="text-sm font-bold text-neutral-900">
                        {mockCalculations.affordability.serviceability}%
                      </span>
                    </div>
                    <div className="w-full bg-neutral-200 rounded-full h-2">
                      <div 
                        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${mockCalculations.affordability.serviceability}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-3 p-4 bg-success-50 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-success-600" />
                    <div>
                      <div className="font-medium text-success-700">LMI Not Required</div>
                      <div className="text-sm text-success-600">
                        Your deposit is above 20% threshold
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Borrowing Capacity Breakdown */}
            <Card variant="elevated">
              <CardHeader padding="lg">
                <CardTitle className="flex items-center gap-3">
                  <PieChart className="w-6 h-6 text-primary-600" />
                  Borrowing Capacity Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent padding="lg">
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-primary-500 rounded-full" />
                      <span className="text-sm font-medium text-neutral-700">Principal & Interest</span>
                    </div>
                    <span className="text-sm font-bold text-neutral-900">
                      {formatCurrency(3800)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-warning-500 rounded-full" />
                      <span className="text-sm font-medium text-neutral-700">Council Rates</span>
                    </div>
                    <span className="text-sm font-bold text-neutral-900">
                      {formatCurrency(150)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-danger-500 rounded-full" />
                      <span className="text-sm font-medium text-neutral-700">Insurance</span>
                    </div>
                    <span className="text-sm font-bold text-neutral-900">
                      {formatCurrency(180)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-success-500 rounded-full" />
                      <span className="text-sm font-medium text-neutral-700">Maintenance Buffer</span>
                    </div>
                    <span className="text-sm font-bold text-neutral-900">
                      {formatCurrency(70)}
                    </span>
                  </div>

                  <div className="border-t border-neutral-200 pt-4 mt-4">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-neutral-900">Total Monthly Cost</span>
                      <span className="text-lg font-bold text-primary-600">
                        {formatCurrency(mockCalculations.affordability.monthlyRepayment)}
                      </span>
                    </div>
                  </div>

                  <div className="p-4 bg-gradient-to-r from-neutral-50 to-primary-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Info className="w-4 h-4 text-primary-600" />
                      <span className="text-sm font-medium text-neutral-900">
                        Recommendation
                      </span>
                    </div>
                    <div className="text-sm text-neutral-600">
                      Based on your income and expenses, you can comfortably afford this property
                      with a safety margin for unexpected costs.
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeCalculator === "roi" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* ROI Overview */}
            <Card variant="elevated">
              <CardHeader padding="lg">
                <CardTitle className="flex items-center gap-3">
                  <TrendingUp className="w-6 h-6 text-primary-600" />
                  Investment Returns
                </CardTitle>
              </CardHeader>
              <CardContent padding="lg">
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-success-50 rounded-lg">
                      <div className="text-2xl font-bold text-success-600">
                        {formatPercentage(mockCalculations.roiProjections.grossYield)}
                      </div>
                      <div className="text-sm text-neutral-700">Gross Yield</div>
                    </div>
                    <div className="text-center p-4 bg-warning-50 rounded-lg">
                      <div className="text-2xl font-bold text-warning-600">
                        {formatPercentage(mockCalculations.roiProjections.netYield)}
                      </div>
                      <div className="text-sm text-neutral-700">Net Yield</div>
                    </div>
                  </div>

                  <div className="p-6 bg-gradient-to-br from-primary-50 to-trust-50 rounded-xl">
                    <div className="text-center">
                      <div className="text-3xl font-heading font-bold text-primary-600 mb-2">
                        {formatPercentage(mockCalculations.roiProjections.fiveYearROI)}
                      </div>
                      <div className="text-lg font-medium text-neutral-700">5-Year ROI</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-600">Annual Rental Income</span>
                      <span className="font-semibold text-neutral-900">
                        {formatCurrency(mockCalculations.roiProjections.annualRent)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-600">Weekly Rent</span>
                      <span className="font-semibold text-neutral-900">
                        {formatCurrency(mockCalculations.roiProjections.weeklyRent)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-600">Monthly Cash Flow</span>
                      <span className={cn(
                        "font-semibold",
                        mockCalculations.roiProjections.cashFlow < 0 
                          ? "text-danger-600" 
                          : "text-success-600"
                      )}>
                        {mockCalculations.roiProjections.cashFlow < 0 ? "-" : "+"}
                        {formatCurrency(Math.abs(mockCalculations.roiProjections.cashFlow))}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Growth Projections */}
            <Card variant="elevated">
              <CardHeader padding="lg">
                <CardTitle className="flex items-center gap-3">
                  <Target className="w-6 h-6 text-primary-600" />
                  Growth Projections
                </CardTitle>
              </CardHeader>
              <CardContent padding="lg">
                <div className="space-y-6">
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-medium text-neutral-900">10-Year Projection</span>
                      <span className="text-xl font-bold text-primary-600">
                        {formatPercentage(mockCalculations.roiProjections.tenYearROI)}
                      </span>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-neutral-600">Initial Investment</span>
                        <span className="font-medium">{formatCurrency(170000)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-neutral-600">Projected Value</span>
                        <span className="font-medium">{formatCurrency(1280000)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-neutral-600">Total Return</span>
                        <span className="font-medium text-success-600">
                          {formatCurrency(327600)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="text-sm font-medium text-neutral-700 mb-3">
                      Investment Scenario Analysis
                    </div>
                    
                    <div className="p-3 bg-success-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle className="w-4 h-4 text-success-600" />
                        <span className="text-sm font-medium text-success-700">Best Case</span>
                      </div>
                      <div className="text-sm text-success-600">
                        6% annual growth, 95% occupancy: {formatPercentage(125.6)} ROI
                      </div>
                    </div>

                    <div className="p-3 bg-warning-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <Target className="w-4 h-4 text-warning-600" />
                        <span className="text-sm font-medium text-warning-700">Base Case</span>
                      </div>
                      <div className="text-sm text-warning-600">
                        4% annual growth, 90% occupancy: {formatPercentage(mockCalculations.roiProjections.tenYearROI)} ROI
                      </div>
                    </div>

                    <div className="p-3 bg-danger-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <AlertTriangle className="w-4 h-4 text-danger-600" />
                        <span className="text-sm font-medium text-danger-700">Worst Case</span>
                      </div>
                      <div className="text-sm text-danger-600">
                        2% annual growth, 80% occupancy: {formatPercentage(58.2)} ROI
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeCalculator === "tax" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Tax Deductions */}
            <Card variant="elevated">
              <CardHeader padding="lg">
                <CardTitle className="flex items-center gap-3">
                  <Calculator className="w-6 h-6 text-primary-600" />
                  Tax Deductions & Benefits
                </CardTitle>
              </CardHeader>
              <CardContent padding="lg">
                <div className="space-y-4">
                  <div className="p-4 bg-success-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-success-600 mb-1">
                        {formatCurrency(mockCalculations.taxAnalysis.annualDeductions)}
                      </div>
                      <div className="text-sm text-success-700">Total Annual Deductions</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Interest on Investment Loan</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(35000)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Property Management Fees</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(2500)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Building Depreciation</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(mockCalculations.taxAnalysis.depreciation)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Maintenance & Repairs</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(mockCalculations.taxAnalysis.maintenanceDeductions)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Council Rates & Insurance</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(3200)}
                      </span>
                    </div>
                  </div>

                  <div className="border-t border-neutral-200 pt-4">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-neutral-900">Annual Tax Savings</span>
                      <span className="text-lg font-bold text-success-600">
                        {formatCurrency(mockCalculations.taxAnalysis.taxSavings)}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Capital Gains Analysis */}
            <Card variant="elevated">
              <CardHeader padding="lg">
                <CardTitle className="flex items-center gap-3">
                  <TrendingUp className="w-6 h-6 text-primary-600" />
                  Capital Gains Analysis
                </CardTitle>
              </CardHeader>
              <CardContent padding="lg">
                <div className="space-y-6">
                  <div className="p-4 bg-warning-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-warning-600 mb-1">
                        {formatCurrency(mockCalculations.taxAnalysis.cgTaxLiability)}
                      </div>
                      <div className="text-sm text-warning-700">Estimated CGT Liability</div>
                      <div className="text-xs text-warning-600 mt-1">
                        After 50% discount (held >12 months)
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="text-sm font-medium text-neutral-700 mb-2">
                      CGT Calculation Breakdown
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600">Sale Price (projected)</span>
                      <span className="font-medium">{formatCurrency(1200000)}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600">Purchase Price + Costs</span>
                      <span className="font-medium">{formatCurrency(870000)}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600">Capital Gain</span>
                      <span className="font-medium text-success-600">{formatCurrency(330000)}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600">50% CGT Discount</span>
                      <span className="font-medium text-primary-600">-{formatCurrency(165000)}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm border-t border-neutral-200 pt-2">
                      <span className="font-medium text-neutral-900">Taxable Capital Gain</span>
                      <span className="font-bold text-neutral-900">{formatCurrency(165000)}</span>
                    </div>
                  </div>

                  <div className="p-4 bg-gradient-to-r from-neutral-50 to-primary-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Info className="w-4 h-4 text-primary-600" />
                      <span className="text-sm font-medium text-neutral-900">
                        Tax Planning Tip
                      </span>
                    </div>
                    <div className="text-sm text-neutral-600">
                      Consider timing the sale to coincide with a lower income year to minimize
                      your marginal tax rate on capital gains.
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeCalculator === "insurance" && (
          <Card variant="elevated">
            <CardHeader padding="lg">
              <CardTitle className="flex items-center gap-3">
                <Shield className="w-6 h-6 text-primary-600" />
                Insurance Cost Analysis
              </CardTitle>
            </CardHeader>
            <CardContent padding="lg">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-6">
                  <div className="p-6 bg-gradient-to-br from-primary-50 to-trust-50 rounded-xl">
                    <div className="text-center">
                      <div className="text-3xl font-heading font-bold text-primary-600 mb-2">
                        {formatCurrency(mockCalculations.insuranceEstimates.totalAnnual)}
                      </div>
                      <div className="text-lg font-medium text-neutral-700">Total Annual Premium</div>
                      <div className="text-sm text-neutral-500 mt-1">
                        {formatCurrency(mockCalculations.insuranceEstimates.monthlyPremium)}/month
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Building className="w-4 h-4 text-neutral-500" />
                        <span className="text-sm text-neutral-700">Building Insurance</span>
                      </div>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(mockCalculations.insuranceEstimates.buildingInsurance)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Home className="w-4 h-4 text-neutral-500" />
                        <span className="text-sm text-neutral-700">Contents Insurance</span>
                      </div>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(mockCalculations.insuranceEstimates.contentsInsurance)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Shield className="w-4 h-4 text-neutral-500" />
                        <span className="text-sm text-neutral-700">Landlord Protection</span>
                      </div>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(mockCalculations.insuranceEstimates.publicLiabilityInsurance)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="p-4 bg-success-50 rounded-lg">
                    <div className="flex items-center gap-3 mb-3">
                      <CheckCircle className="w-5 h-5 text-success-600" />
                      <span className="font-medium text-success-700">Recommended Coverage</span>
                    </div>
                    <div className="space-y-2 text-sm text-success-600">
                      <div>• Full replacement value building cover</div>
                      <div>• $50,000 contents protection</div>
                      <div>• $20M public liability coverage</div>
                      <div>• Rental income protection</div>
                    </div>
                  </div>

                  <div className="p-4 bg-warning-50 rounded-lg">
                    <div className="flex items-center gap-3 mb-3">
                      <AlertTriangle className="w-5 h-5 text-warning-600" />
                      <span className="font-medium text-warning-700">Important Notes</span>
                    </div>
                    <div className="space-y-2 text-sm text-warning-600">
                      <div>• Premiums vary by location and property type</div>
                      <div>• Consider flood and storm coverage</div>
                      <div>• Review coverage annually</div>
                      <div>• Compare quotes from multiple insurers</div>
                    </div>
                  </div>

                  <Button variant="outline" fullWidth className="flex items-center gap-2">
                    Get Insurance Quotes
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </motion.div>
    </div>
  );
};

export default FinancialAnalysisPage;
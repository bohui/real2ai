import React, { useState, useEffect } from "react";
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
  Shield,
} from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import StatusBadge from "@/components/ui/StatusBadge";
import { cn } from "@/utils";

// Financial calculation interfaces
interface AffordabilityResults {
  maxLoanAmount: number;
  monthlyRepayment: number;
  depositRequired: number;
  totalPropertyBudget: number;
  serviceability: number;
  lmiRequired: boolean;
  principalAndInterest: number;
  otherCosts: {
    councilRates: number;
    insurance: number;
    maintenance: number;
  };
}

interface ROIProjections {
  purchasePrice: number;
  weeklyRent: number;
  annualRent: number;
  grossYield: number;
  netYield: number;
  fiveYearROI: number;
  tenYearROI: number;
  cashFlow: number;
  projectedValue10Year: number;
  totalReturn10Year: number;
}

interface TaxAnalysis {
  annualDeductions: number;
  taxSavings: number;
  depreciation: number;
  maintenanceDeductions: number;
  cgTaxLiability: number;
  negativeGearingBenefit: number;
  interestDeduction: number;
  managementFees: number;
  otherDeductions: number;
}

interface InsuranceEstimates {
  buildingInsurance: number;
  contentsInsurance: number;
  publicLiabilityInsurance: number;
  totalAnnual: number;
  monthlyPremium: number;
}

interface FinancialCalculations {
  affordability: AffordabilityResults | null;
  roiProjections: ROIProjections | null;
  taxAnalysis: TaxAnalysis | null;
  insuranceEstimates: InsuranceEstimates | null;
}

const FinancialAnalysisPage: React.FC = () => {
  // UI State
  const [activeCalculator, setActiveCalculator] = useState<"affordability" | "roi" | "tax" | "insurance">("affordability");
  
  // Input Parameters
  const [propertyPrice, setPropertyPrice] = useState(850000);
  const [annualIncome, setAnnualIncome] = useState(120000);
  const [deposit, setDeposit] = useState(170000);
  const [interestRate, setInterestRate] = useState(6.5);
  const [weeklyRent, setWeeklyRent] = useState(650);
  const [taxRate, setTaxRate] = useState(35); // Marginal tax rate %
  const [loanTerm, setLoanTerm] = useState(30); // years
  
  // Data State
  const [calculations, setCalculations] = useState<FinancialCalculations>({
    affordability: null,
    roiProjections: null,
    taxAnalysis: null,
    insuranceEstimates: null,
  });
  
  // Loading and Error States
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load initial data and perform calculations
  useEffect(() => {
    calculateFinancials();
  }, [propertyPrice, annualIncome, deposit, interestRate, weeklyRent, taxRate, loanTerm]);
  
  const calculatorTabs = [
    { id: "affordability" as const, label: "Affordability", icon: Home },
    { id: "roi" as const, label: "ROI Analysis", icon: TrendingUp },
    { id: "tax" as const, label: "Tax Analysis", icon: Calculator },
    { id: "insurance" as const, label: "Insurance", icon: Shield },
  ];
  
  const calculateFinancials = async () => {
    setIsCalculating(true);
    setError(null);
    
    try {
      // Calculate affordability
      const affordabilityResults = calculateAffordability();
      
      // Calculate ROI projections
      const roiResults = calculateROI();
      
      // Calculate tax analysis
      const taxResults = calculateTaxAnalysis();
      
      // Calculate insurance estimates
      const insuranceResults = calculateInsurance();
      
      setCalculations({
        affordability: affordabilityResults,
        roiProjections: roiResults,
        taxAnalysis: taxResults,
        insuranceEstimates: insuranceResults,
      });
      
    } catch (error) {
      console.error("Financial calculation failed:", error);
      setError("Failed to perform financial calculations. Please check your inputs.");
    } finally {
      setIsCalculating(false);
    }
  };
  
  const calculateAffordability = (): AffordabilityResults => {
    const loanAmount = propertyPrice - deposit;
    const monthlyInterestRate = interestRate / 100 / 12;
    const totalPayments = loanTerm * 12;
    
    // Calculate monthly principal and interest payment
    const monthlyPI = loanAmount * 
      (monthlyInterestRate * Math.pow(1 + monthlyInterestRate, totalPayments)) /
      (Math.pow(1 + monthlyInterestRate, totalPayments) - 1);
    
    // Calculate other monthly costs
    const councilRates = propertyPrice * 0.002 / 12; // 0.2% of property value annually
    const insurance = propertyPrice * 0.0015 / 12; // 0.15% of property value annually
    const maintenance = propertyPrice * 0.01 / 12; // 1% of property value annually
    
    const totalMonthlyCost = monthlyPI + councilRates + insurance + maintenance;
    
    // Calculate serviceability (total monthly payment as % of income)
    const monthlyIncome = annualIncome / 12;
    const serviceability = Math.round((totalMonthlyCost / monthlyIncome) * 100);
    
    // LMI required if deposit < 20%
    const lmiRequired = (deposit / propertyPrice) < 0.2;
    
    return {
      maxLoanAmount: loanAmount,
      monthlyRepayment: Math.round(totalMonthlyCost),
      depositRequired: Math.round(propertyPrice * 0.2), // Standard 20%
      totalPropertyBudget: propertyPrice,
      serviceability,
      lmiRequired,
      principalAndInterest: Math.round(monthlyPI),
      otherCosts: {
        councilRates: Math.round(councilRates),
        insurance: Math.round(insurance),
        maintenance: Math.round(maintenance),
      },
    };
  };
  
  const calculateROI = (): ROIProjections => {
    const annualRent = weeklyRent * 52;
    const grossYield = (annualRent / propertyPrice) * 100;
    
    // Calculate annual expenses (property management, rates, insurance, maintenance)
    const annualExpenses = 
      (annualRent * 0.08) + // 8% management fee
      (propertyPrice * 0.002) + // Council rates
      (propertyPrice * 0.0015) + // Insurance
      (propertyPrice * 0.01); // Maintenance
    
    const netAnnualRent = annualRent - annualExpenses;
    const netYield = (netAnnualRent / propertyPrice) * 100;
    
    // Calculate cash flow (net rent - loan payments)
    const monthlyPI = calculations.affordability?.principalAndInterest || 0;
    const annualLoanPayments = monthlyPI * 12;
    const annualCashFlow = netAnnualRent - annualLoanPayments;
    const monthlyCashFlow = annualCashFlow / 12;
    
    // Project property value growth (4% annually)
    const growthRate = 0.04;
    const projectedValue10Year = propertyPrice * Math.pow(1 + growthRate, 10);
    
    // Calculate total return over 10 years
    const capitalGain = projectedValue10Year - propertyPrice;
    const totalRentalIncome = annualRent * 10;
    const totalExpenses = annualExpenses * 10;
    const totalReturn10Year = capitalGain + totalRentalIncome - totalExpenses;
    const totalROI = (totalReturn10Year / deposit) * 100;
    
    // 5-year projection
    const projectedValue5Year = propertyPrice * Math.pow(1 + growthRate, 5);
    const capitalGain5Year = projectedValue5Year - propertyPrice;
    const totalReturn5Year = capitalGain5Year + (netAnnualRent * 5);
    const fiveYearROI = (totalReturn5Year / deposit) * 100;
    
    return {
      purchasePrice: propertyPrice,
      weeklyRent,
      annualRent,
      grossYield: Math.round(grossYield * 10) / 10,
      netYield: Math.round(netYield * 10) / 10,
      fiveYearROI: Math.round(fiveYearROI * 10) / 10,
      tenYearROI: Math.round(totalROI * 10) / 10,
      cashFlow: Math.round(monthlyCashFlow),
      projectedValue10Year: Math.round(projectedValue10Year),
      totalReturn10Year: Math.round(totalReturn10Year),
    };
  };
  
  const calculateTaxAnalysis = (): TaxAnalysis => {
    const loanAmount = propertyPrice - deposit;
    const annualInterest = loanAmount * (interestRate / 100);
    const annualRent = weeklyRent * 52;
    
    // Tax deductible expenses
    const managementFees = annualRent * 0.08;
    const councilRates = propertyPrice * 0.002;
    const insurance = propertyPrice * 0.0015;
    const maintenance = propertyPrice * 0.01;
    const depreciation = Math.min(propertyPrice * 0.025, 40000); // 2.5% or $40k max
    
    const totalDeductions = annualInterest + managementFees + councilRates + 
                           insurance + maintenance + depreciation;
    
    // Tax savings (assuming marginal tax rate)
    const taxSavings = totalDeductions * (taxRate / 100);
    
    // Capital gains tax calculation (10-year projection)
    const projectedValue = propertyPrice * Math.pow(1.04, 10);
    const capitalGain = projectedValue - propertyPrice;
    const discountedGain = capitalGain * 0.5; // 50% CGT discount
    const cgTaxLiability = discountedGain * (taxRate / 100);
    
    // Negative gearing benefit
    const totalExpenses = annualInterest + managementFees + councilRates + insurance + maintenance;
    const negativeGearing = Math.max(0, totalExpenses - annualRent);
    const negativeGearingBenefit = negativeGearing * (taxRate / 100);
    
    return {
      annualDeductions: Math.round(totalDeductions),
      taxSavings: Math.round(taxSavings),
      depreciation: Math.round(depreciation),
      maintenanceDeductions: Math.round(maintenance),
      cgTaxLiability: Math.round(cgTaxLiability),
      negativeGearingBenefit: Math.round(negativeGearingBenefit),
      interestDeduction: Math.round(annualInterest),
      managementFees: Math.round(managementFees),
      otherDeductions: Math.round(councilRates + insurance),
    };
  };
  
  const calculateInsurance = (): InsuranceEstimates => {
    // Insurance costs based on property value
    const buildingInsurance = Math.max(800, propertyPrice * 0.0015); // 0.15% of property value
    const contentsInsurance = 600; // Standard contents coverage
    const publicLiability = 400; // Standard landlord protection
    
    const totalAnnual = buildingInsurance + contentsInsurance + publicLiability;
    const monthlyPremium = totalAnnual / 12;
    
    return {
      buildingInsurance: Math.round(buildingInsurance),
      contentsInsurance: Math.round(contentsInsurance),
      publicLiabilityInsurance: Math.round(publicLiability),
      totalAnnual: Math.round(totalAnnual),
      monthlyPremium: Math.round(monthlyPremium),
    };
  };
  
  const handleCalculate = () => {
    calculateFinancials();
  };
  

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
                  Interest Rate (%)
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
            
            {/* Additional Parameters Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Weekly Rent
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                  <input
                    type="number"
                    value={weeklyRent}
                    onChange={(e) => setWeeklyRent(Number(e.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Loan Term (years)
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                  <select
                    value={loanTerm}
                    onChange={(e) => setLoanTerm(Number(e.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={15}>15 years</option>
                    <option value={20}>20 years</option>
                    <option value={25}>25 years</option>
                    <option value={30}>30 years</option>
                  </select>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Tax Rate (%)
                </label>
                <div className="relative">
                  <Percent className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                  <select
                    value={taxRate}
                    onChange={(e) => setTaxRate(Number(e.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={19}>19% - Low income</option>
                    <option value={32.5}>32.5% - Medium income</option>
                    <option value={37}>37% - High income</option>
                    <option value={45}>45% - Top income</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-between items-center">
              <div className="text-sm text-neutral-600">
                <span className="font-medium">LVR:</span> {((propertyPrice - deposit) / propertyPrice * 100).toFixed(1)}% | 
                <span className="font-medium">Deposit %:</span> {(deposit / propertyPrice * 100).toFixed(1)}%
              </div>
              <div className="flex gap-3">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => {
                    // Load sample property data
                    setPropertyPrice(850000);
                    setDeposit(170000);
                    setWeeklyRent(650);
                    setInterestRate(6.5);
                  }}
                >
                  Load Sample
                </Button>
                <Button 
                  variant="primary" 
                  className="px-8" 
                  onClick={handleCalculate}
                  disabled={isCalculating}
                >
                  {isCalculating ? "Calculating..." : "Recalculate"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <div className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg">
            <div className="flex items-center gap-2 text-danger-700">
              <AlertTriangle className="w-5 h-5" />
              <span className="font-medium">{error}</span>
            </div>
          </div>
        </motion.div>
      )}
      
      {/* Loading State */}
      {isCalculating && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-3"></div>
            <p className="text-neutral-600">Performing financial calculations...</p>
          </div>
        </motion.div>
      )}
      
      {/* Results Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {/* Empty State */}
        {!isCalculating && !calculations.affordability && !calculations.roiProjections && !calculations.taxAnalysis && !calculations.insuranceEstimates && (
          <div className="text-center py-12">
            <Calculator className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-neutral-700 mb-2">Ready to Calculate</h3>
            <p className="text-neutral-500 mb-6">Adjust your parameters above and click "Recalculate" to see detailed financial analysis.</p>
            <Button variant="primary" onClick={handleCalculate}>
              Start Financial Analysis
            </Button>
          </div>
        )}
        
        {activeCalculator === "affordability" && calculations.affordability && (
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
                      {formatCurrency(calculations.affordability.maxLoanAmount)}
                    </div>
                    <div className="text-lg font-medium text-neutral-700">Maximum Loan Amount</div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-neutral-50 rounded-lg">
                      <div className="text-xl font-bold text-neutral-900">
                        {formatCurrency(calculations.affordability.monthlyRepayment)}
                      </div>
                      <div className="text-sm text-neutral-500">Monthly Repayment</div>
                    </div>
                    <div className="text-center p-4 bg-neutral-50 rounded-lg">
                      <div className="text-xl font-bold text-neutral-900">
                        {formatCurrency(calculations.affordability.depositRequired)}
                      </div>
                      <div className="text-sm text-neutral-500">Deposit Required</div>
                    </div>
                  </div>

                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-neutral-700">Serviceability</span>
                      <span className="text-sm font-bold text-neutral-900">
                        {calculations.affordability.serviceability}%
                      </span>
                    </div>
                    <div className="w-full bg-neutral-200 rounded-full h-2">
                      <div 
                        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(calculations.affordability.serviceability, 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className={cn(
                    "flex items-center gap-3 p-4 rounded-lg",
                    calculations.affordability.lmiRequired 
                      ? "bg-warning-50" 
                      : "bg-success-50"
                  )}>
                    {calculations.affordability.lmiRequired ? (
                      <AlertTriangle className="w-5 h-5 text-warning-600" />
                    ) : (
                      <CheckCircle className="w-5 h-5 text-success-600" />
                    )}
                    <div>
                      <div className={cn(
                        "font-medium",
                        calculations.affordability.lmiRequired 
                          ? "text-warning-700" 
                          : "text-success-700"
                      )}>
                        {calculations.affordability.lmiRequired ? "LMI Required" : "LMI Not Required"}
                      </div>
                      <div className={cn(
                        "text-sm",
                        calculations.affordability.lmiRequired 
                          ? "text-warning-600" 
                          : "text-success-600"
                      )}>
                        {calculations.affordability.lmiRequired 
                          ? "Deposit is below 20% - LMI will apply" 
                          : "Your deposit is above 20% threshold"
                        }
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
                      {formatCurrency(calculations.affordability.principalAndInterest)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-warning-500 rounded-full" />
                      <span className="text-sm font-medium text-neutral-700">Council Rates</span>
                    </div>
                    <span className="text-sm font-bold text-neutral-900">
                      {formatCurrency(calculations.affordability.otherCosts.councilRates)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-danger-500 rounded-full" />
                      <span className="text-sm font-medium text-neutral-700">Insurance</span>
                    </div>
                    <span className="text-sm font-bold text-neutral-900">
                      {formatCurrency(calculations.affordability.otherCosts.insurance)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-success-500 rounded-full" />
                      <span className="text-sm font-medium text-neutral-700">Maintenance Buffer</span>
                    </div>
                    <span className="text-sm font-bold text-neutral-900">
                      {formatCurrency(calculations.affordability.otherCosts.maintenance)}
                    </span>
                  </div>

                  <div className="border-t border-neutral-200 pt-4 mt-4">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-neutral-900">Total Monthly Cost</span>
                      <span className="text-lg font-bold text-primary-600">
                        {formatCurrency(calculations.affordability.monthlyRepayment)}
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

        {activeCalculator === "roi" && calculations.roiProjections && (
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
                        {formatPercentage(calculations.roiProjections.grossYield)}
                      </div>
                      <div className="text-sm text-neutral-700">Gross Yield</div>
                    </div>
                    <div className="text-center p-4 bg-warning-50 rounded-lg">
                      <div className="text-2xl font-bold text-warning-600">
                        {formatPercentage(calculations.roiProjections.netYield)}
                      </div>
                      <div className="text-sm text-neutral-700">Net Yield</div>
                    </div>
                  </div>

                  <div className="p-6 bg-gradient-to-br from-primary-50 to-trust-50 rounded-xl">
                    <div className="text-center">
                      <div className="text-3xl font-heading font-bold text-primary-600 mb-2">
                        {formatPercentage(calculations.roiProjections.fiveYearROI)}
                      </div>
                      <div className="text-lg font-medium text-neutral-700">5-Year ROI</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-600">Annual Rental Income</span>
                      <span className="font-semibold text-neutral-900">
                        {formatCurrency(calculations.roiProjections.annualRent)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-600">Weekly Rent</span>
                      <span className="font-semibold text-neutral-900">
                        {formatCurrency(calculations.roiProjections.weeklyRent)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-600">Monthly Cash Flow</span>
                      <span className={cn(
                        "font-semibold",
                        calculations.roiProjections.cashFlow < 0 
                          ? "text-danger-600" 
                          : "text-success-600"
                      )}>
                        {calculations.roiProjections.cashFlow < 0 ? "-" : "+"}
                        {formatCurrency(Math.abs(calculations.roiProjections.cashFlow))}
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
                        {formatPercentage(calculations.roiProjections.tenYearROI)}
                      </span>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-neutral-600">Initial Investment</span>
                        <span className="font-medium">{formatCurrency(deposit)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-neutral-600">Projected Value</span>
                        <span className="font-medium">{formatCurrency(calculations.roiProjections.projectedValue10Year)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-neutral-600">Total Return</span>
                        <span className="font-medium text-success-600">
                          {formatCurrency(calculations.roiProjections.totalReturn10Year)}
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
                        4% annual growth, 90% occupancy: {formatPercentage(calculations.roiProjections.tenYearROI)} ROI
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

        {activeCalculator === "tax" && calculations.taxAnalysis && (
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
                        {formatCurrency(calculations.taxAnalysis.annualDeductions)}
                      </div>
                      <div className="text-sm text-success-700">Total Annual Deductions</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Interest on Investment Loan</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(calculations.taxAnalysis.interestDeduction)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Property Management Fees</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(calculations.taxAnalysis.managementFees)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Building Depreciation</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(calculations.taxAnalysis.depreciation)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Maintenance & Repairs</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(calculations.taxAnalysis.maintenanceDeductions)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <span className="text-sm text-neutral-600">Council Rates & Insurance</span>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(calculations.taxAnalysis.otherDeductions)}
                      </span>
                    </div>
                  </div>

                  <div className="border-t border-neutral-200 pt-4">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-neutral-900">Annual Tax Savings</span>
                      <span className="text-lg font-bold text-success-600">
                        {formatCurrency(calculations.taxAnalysis.taxSavings)}
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
                        {formatCurrency(calculations.taxAnalysis.cgTaxLiability)}
                      </div>
                      <div className="text-sm text-warning-700">Estimated CGT Liability</div>
                      <div className="text-xs text-warning-600 mt-1">
                        After 50% discount (held greater than 12 months)
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

        {activeCalculator === "insurance" && calculations.insuranceEstimates && (
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
                        {formatCurrency(calculations.insuranceEstimates.totalAnnual)}
                      </div>
                      <div className="text-lg font-medium text-neutral-700">Total Annual Premium</div>
                      <div className="text-sm text-neutral-500 mt-1">
                        {formatCurrency(calculations.insuranceEstimates.monthlyPremium)}/month
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
                        {formatCurrency(calculations.insuranceEstimates.buildingInsurance)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Home className="w-4 h-4 text-neutral-500" />
                        <span className="text-sm text-neutral-700">Contents Insurance</span>
                      </div>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(calculations.insuranceEstimates.contentsInsurance)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Shield className="w-4 h-4 text-neutral-500" />
                        <span className="text-sm text-neutral-700">Landlord Protection</span>
                      </div>
                      <span className="font-medium text-neutral-900">
                        {formatCurrency(calculations.insuranceEstimates.publicLiabilityInsurance)}
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
import React from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  ArrowRight, 
  TrendingUp, 
  FileText, 
  Clock, 
  AlertTriangle,
  CheckCircle,
  DollarSign,
  Calendar
} from 'lucide-react'

import Button from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useAnalysisStore } from '@/store/analysisStore'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/utils'

const DashboardPage: React.FC = () => {
  const { recentAnalyses } = useAnalysisStore()
  const { user } = useAuthStore()

  // Calculate dashboard stats
  const totalAnalyses = recentAnalyses.length
  const completedAnalyses = recentAnalyses.filter(a => a.analysis_status === 'completed').length
  const averageRiskScore = recentAnalyses.length > 0 
    ? recentAnalyses.reduce((sum, a) => sum + a.executive_summary.overall_risk_score, 0) / recentAnalyses.length 
    : 0
  const highRiskCount = recentAnalyses.filter(a => a.executive_summary.overall_risk_score >= 7).length

  const stats = [
    {
      title: 'Total Analyses',
      value: totalAnalyses,
      change: '+12%',
      trend: 'up',
      icon: FileText,
      color: 'primary'
    },
    {
      title: 'Average Risk Score',
      value: averageRiskScore.toFixed(1),
      change: '-0.3',
      trend: 'down',
      icon: TrendingUp,
      color: 'success'
    },
    {
      title: 'High Risk Contracts',
      value: highRiskCount,
      change: '-2',
      trend: 'down',
      icon: AlertTriangle,
      color: 'warning'
    },
    {
      title: 'Credits Remaining',
      value: user?.credits_remaining || 0,
      change: user?.subscription_status === 'active' ? 'Unlimited' : 'Limited',
      trend: 'neutral',
      icon: DollarSign,
      color: 'primary'
    }
  ]

  const quickActions = [
    {
      title: 'New Analysis',
      description: 'Upload and analyze a new contract',
      href: '/app/analysis',
      icon: FileText,
      color: 'primary'
    },
    {
      title: 'View History',
      description: 'Browse your previous analyses',
      href: '/app/history',
      icon: Clock,
      color: 'secondary'
    }
  ]

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">
            Welcome back, {user?.email.split('@')[0]}
          </h1>
          <p className="text-neutral-600 mt-1">
            Here's what's happening with your contract analyses
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-3">
          <div className="text-right">
            <div className="text-sm text-neutral-500">Last login</div>
            <div className="font-medium text-neutral-900">
              {new Date().toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const IconComponent = stat.icon
          
          return (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <Card>
                <CardContent padding="lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-neutral-600">{stat.title}</p>
                      <p className="text-2xl font-bold text-neutral-900 mt-1">{stat.value}</p>
                      <div className="flex items-center mt-2">
                        <span className={cn(
                          'text-sm font-medium',
                          stat.trend === 'up' ? 'text-success-600' :
                          stat.trend === 'down' ? 'text-danger-600' :
                          'text-neutral-600'
                        )}>
                          {stat.change}
                        </span>
                        <span className="text-neutral-500 text-sm ml-1">vs last month</span>
                      </div>
                    </div>
                    <div className={cn(
                      'w-12 h-12 rounded-lg flex items-center justify-center',
                      stat.color === 'primary' ? 'bg-primary-100' :
                      stat.color === 'success' ? 'bg-success-100' :
                      stat.color === 'warning' ? 'bg-warning-100' :
                      'bg-secondary-100'
                    )}>
                      <IconComponent className={cn(
                        'w-6 h-6',
                        stat.color === 'primary' ? 'text-primary-600' :
                        stat.color === 'success' ? 'text-success-600' :
                        stat.color === 'warning' ? 'text-warning-600' :
                        'text-secondary-600'
                      )} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Quick Actions */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {quickActions.map((action) => {
                  const IconComponent = action.icon
                  
                  return (
                    <Link
                      key={action.title}
                      to={action.href}
                      className="block p-4 rounded-lg border border-neutral-200 hover:border-primary-300 hover:bg-primary-50 transition-all duration-200 group"
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
                          action.color === 'primary' 
                            ? 'bg-primary-100 text-primary-600 group-hover:bg-primary-200' 
                            : 'bg-secondary-100 text-secondary-600 group-hover:bg-secondary-200'
                        )}>
                          <IconComponent className="w-5 h-5" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-medium text-neutral-900">{action.title}</h3>
                          <p className="text-sm text-neutral-500">{action.description}</p>
                        </div>
                        <ArrowRight className="w-4 h-4 text-neutral-400 group-hover:text-primary-600 transition-colors" />
                      </div>
                    </Link>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Analyses */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Recent Analyses</CardTitle>
                <Link to="/app/history">
                  <Button variant="ghost" size="sm">
                    View all
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {recentAnalyses.length > 0 ? (
                <div className="space-y-4">
                  {recentAnalyses.slice(0, 5).map((analysis) => (
                    <div key={analysis.contract_id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-neutral-50 transition-colors">
                      <div className="flex-shrink-0">
                        <div className={cn(
                          'w-10 h-10 rounded-lg flex items-center justify-center',
                          analysis.analysis_status === 'completed' ? 'bg-success-100' :
                          analysis.analysis_status === 'processing' ? 'bg-warning-100' :
                          'bg-neutral-100'
                        )}>
                          {analysis.analysis_status === 'completed' ? (
                            <CheckCircle className="w-5 h-5 text-success-600" />
                          ) : (
                            <Clock className="w-5 h-5 text-warning-600" />
                          )}
                        </div>
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-neutral-900 truncate">
                            Contract Analysis
                          </h3>
                          <span className={cn(
                            'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                            analysis.analysis_status === 'completed' ? 'bg-success-100 text-success-700' :
                            analysis.analysis_status === 'processing' ? 'bg-warning-100 text-warning-700' :
                            'bg-neutral-100 text-neutral-700'
                          )}>
                            {analysis.analysis_status}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 mt-1">
                          <p className="text-sm text-neutral-500">
                            {new Date(analysis.analysis_timestamp).toLocaleDateString()}
                          </p>
                          {analysis.analysis_status === 'completed' && (
                            <div className="flex items-center gap-1">
                              <span className="text-sm text-neutral-500">Risk Score:</span>
                              <span className={cn(
                                'text-sm font-medium',
                                analysis.executive_summary.overall_risk_score >= 7 ? 'text-danger-600' :
                                analysis.executive_summary.overall_risk_score >= 5 ? 'text-warning-600' :
                                'text-success-600'
                              )}>
                                {analysis.executive_summary.overall_risk_score.toFixed(1)}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex-shrink-0">
                        <Link to={`/app/analysis/${analysis.contract_id}`}>
                          <Button variant="ghost" size="sm">
                            View
                          </Button>
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <FileText className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-neutral-900 mb-2">
                    No analyses yet
                  </h3>
                  <p className="text-neutral-500 mb-4">
                    Upload your first contract to get started with AI-powered analysis
                  </p>
                  <Link to="/app/analysis">
                    <Button variant="primary">
                      Start Analysis
                    </Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Australian Market Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Australian Market Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600 mb-1">2.1%</div>
              <div className="text-sm text-neutral-500">Interest Rate Change</div>
              <div className="text-xs text-neutral-400 mt-1">RBA Cash Rate</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-success-600 mb-1">+5.2%</div>
              <div className="text-sm text-neutral-500">Property Value Growth</div>
              <div className="text-xs text-neutral-400 mt-1">National Average</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-warning-600 mb-1">28 days</div>
              <div className="text-sm text-neutral-500">Settlement Period</div>
              <div className="text-xs text-neutral-400 mt-1">Average</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default DashboardPage
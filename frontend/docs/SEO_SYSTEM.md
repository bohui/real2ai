# Real2AI SEO System Documentation

A comprehensive dynamic meta tag system and SEO optimization framework built for React 19 compatibility and optimal search engine performance.

## 🌟 Features

### Dynamic Meta Tag Management
- **Real-time Updates**: Meta tags update automatically with route changes and content updates
- **React 19 Compatible**: Native DOM API implementation (no react-helmet-async dependency)
- **Template System**: Dynamic content generation based on property data, analysis results, etc.
- **Fallback Support**: Graceful degradation with sensible defaults

### Structured Data Integration
- **JSON-LD Support**: Rich structured data for search engines
- **Multiple Schema Types**: Organization, WebSite, Article, Property, Service schemas
- **Dynamic Generation**: Context-aware structured data based on page content
- **Validation**: Built-in JSON-LD validation and error checking

### SEO Performance Monitoring
- **Real-time Analysis**: Live SEO score calculation and issue detection
- **Performance Metrics**: Core Web Vitals tracking and performance monitoring
- **Development Tools**: Visual SEO debugging tools for development
- **Historical Tracking**: SEO score trends and performance history

### Route-Specific Optimization
- **Page-Specific Configs**: Unique SEO metadata for each route
- **Dynamic Content**: Templates that adapt to user data and analysis results
- **Breadcrumb Support**: Automatic breadcrumb structured data
- **Canonical URLs**: Proper canonical URL management

## 📁 Architecture

```
src/
├── components/seo/
│   ├── SEOHead.tsx           # Core SEO component (React 19 compatible)
│   ├── RootSEO.tsx          # App-level SEO wrapper
│   ├── withSEO.tsx          # Higher-order component for SEO
│   ├── SEODevTools.tsx      # Development debugging tools
│   ├── SEOFloatingButton.tsx # Dev tools access button
│   └── index.ts             # Centralized exports
├── contexts/
│   └── SEOContext.tsx       # Global SEO state management
├── config/
│   └── seoConfig.ts         # SEO configurations and templates
├── hooks/
│   └── useSEO.ts           # Enhanced SEO hook with dynamic updates
├── utils/
│   ├── structuredData.ts   # Structured data generators
│   ├── seoUtils.ts         # Sitemap and robots.txt utilities
│   └── seoMonitoring.ts    # Performance monitoring and analytics
├── scripts/
│   └── generateSitemap.js  # Build-time sitemap generation
└── examples/
    └── seoUsage.tsx        # Usage examples and patterns
```

## 🚀 Quick Start

### 1. App-Level Setup

The SEO system is automatically integrated into your app:

```tsx
// App.tsx - Already configured
import SEOProvider from '@/contexts/SEOContext';
import RootSEO from '@/components/seo/RootSEO';

function App() {
  return (
    <Router>
      <SEOProvider>
        <RootSEO />
        {/* Your app content */}
      </SEOProvider>
    </Router>
  );
}
```

### 2. Page-Level SEO

Use the `usePageSEO` hook in your page components:

```tsx
import { usePageSEO } from '@/contexts/SEOContext';

const DashboardPage: React.FC = () => {
  usePageSEO({
    title: 'Dashboard - Real2AI',
    description: 'Your Real2AI dashboard with AI-powered insights.',
    keywords: ['dashboard', 'real estate', 'AI analytics'],
    canonical: '/app/dashboard',
    noIndex: true // Private page
  });

  return <div>Dashboard content...</div>;
};
```

### 3. Dynamic SEO Updates

For pages with changing content:

```tsx
const ContractAnalysisPage: React.FC = () => {
  const [analysis, setAnalysis] = useState(null);
  
  // Dynamic SEO based on analysis data
  const propertyAddress = analysis?.property_address;
  const riskScore = analysis?.risk_score;
  
  usePageSEO(
    {
      title: propertyAddress 
        ? `Analysis - ${propertyAddress} - Real2AI`
        : 'Contract Analysis - Real2AI',
      description: propertyAddress && riskScore
        ? `AI analysis of ${propertyAddress}. Risk: ${riskScore >= 7 ? 'high' : 'low'}.`
        : 'AI-powered contract analysis for Australian real estate.',
      canonical: '/app/analysis',
      ogType: 'article'
    },
    propertyAddress ? {
      address: propertyAddress,
      riskScore: riskScore,
      publishedTime: new Date().toISOString()
    } : undefined
  );

  return <div>Analysis content...</div>;
};
```

## 📋 Page-Specific SEO Configurations

The system includes optimized SEO for all Real2AI pages:

### App Pages (Private - noIndex: true)
- **Dashboard**: "Real2AI Dashboard - Contract Analysis Management"
- **Analysis**: "Contract Analysis - [Property Address] - Real2AI"  
- **History**: "Analysis History - Real2AI"
- **Property Intelligence**: "Property Intelligence - [Suburb/Address] - Real2AI"
- **Market Analysis**: "Market Analysis - Australian Real Estate - Real2AI"
- **Financial Analysis**: "Financial Analysis - Real Estate ROI - Real2AI"
- **Reports**: "Reports - Real2AI"
- **Settings**: "Settings - Real2AI"

### Auth Pages (Public)
- **Login**: "Login - Real2AI" 
- **Register**: "Register - Real2AI"

## 🔧 Configuration

### SEO Templates

Dynamic content templates in `src/config/seoConfig.ts`:

```typescript
export const SEO_TEMPLATES = {
  contractAnalysis: {
    title: (address?: string) => 
      address ? `Contract Analysis - ${address} - Real2AI` : 'Contract Analysis - Real2AI',
    description: (address?: string, riskScore?: number) => {
      if (address && riskScore !== undefined) {
        const riskLevel = riskScore >= 7 ? 'high' : riskScore >= 4 ? 'moderate' : 'low';
        return `Comprehensive AI analysis of ${address}. Risk level: ${riskLevel}.`;
      }
      return 'AI-powered contract analysis for Australian real estate.';
    },
    keywords: (address?: string) => [
      'contract analysis', 'real estate AI', 'property contract',
      ...(address ? [`${address} contract`] : [])
    ]
  }
  // More templates...
};
```

### Base Configuration

```typescript
export const SEO_CONFIG = {
  baseUrl: 'https://real2.ai',
  siteName: 'Real2AI',
  defaultTitle: 'Real2AI - Australian Real Estate AI Assistant',
  titleSeparator: ' - ',
  defaultDescription: 'Advanced AI-powered real estate contract analysis and property intelligence.',
  defaultImage: '/images/og-default.jpg',
  twitterSite: '@Real2AI',
  author: 'Real2AI Team',
  publisher: 'Real2AI Pty Ltd',
};
```

## 🎯 Advanced Features

### Structured Data

Automatic structured data generation:

```tsx
// Automatically generates appropriate structured data
usePageSEO({
  title: 'Contract Analysis - 123 Main St - Real2AI',
  ogType: 'article',
  structuredData: [
    generateArticleData({
      title: 'Contract Analysis - 123 Main St',
      description: 'Professional AI contract analysis',
      section: 'Contract Analysis',
      tags: ['real estate', 'contract analysis']
    }),
    generatePropertyData({
      address: '123 Main St, Sydney NSW',
      propertyType: 'House',
      price: 850000
    })
  ]
});
```

### Higher-Order Component Pattern

For reusable SEO configurations:

```tsx
import { withSEO } from '@/components/seo';

const ReportsPageBase: React.FC = () => <div>Reports</div>;

const ReportsPage = withSEO(ReportsPageBase, {
  staticSEO: {
    title: 'Reports - Real2AI',
    description: 'Generate comprehensive property reports.',
    canonical: '/app/reports'
  }
});
```

### Hook-Based Pattern

For complex SEO logic:

```tsx
import { useSEOForPage } from '@/components/seo';

const PropertyPage: React.FC = () => {
  const { SEOComponent, updateSEO } = useSEOForPage({
    staticSEO: {
      title: 'Properties - Real2AI',
      canonical: '/app/properties'
    }
  });

  // Update SEO based on data changes
  useEffect(() => {
    if (propertyData) {
      updateSEO({
        title: `${propertyData.address} - Property Analysis - Real2AI`,
        description: `AI analysis for ${propertyData.address}`
      });
    }
  }, [propertyData, updateSEO]);

  return (
    <>
      {SEOComponent}
      <div>Property content...</div>
    </>
  );
};
```

## 🛠️ Development Tools

### SEO Dev Tools

In development mode, access real-time SEO analysis:

1. **Floating Button**: Click the search icon in bottom-right corner
2. **Real-time Analysis**: SEO score, issues, and recommendations
3. **Meta Tag Inspector**: View all meta tags and structured data
4. **Performance Metrics**: Core Web Vitals and loading performance

### SEO Monitoring

```typescript
import { enableSEOMonitoring } from '@/utils/seoMonitoring';

// Enable in development
if (process.env.NODE_ENV === 'development') {
  enableSEOMonitoring({
    trackOnRouteChange: true,
    alertOnScoreDrop: 80,
    logToConsole: true
  });
}
```

## 📊 Performance & Monitoring

### SEO Metrics Tracked

- **SEO Score**: 0-100 based on best practices
- **Title Length**: Optimal 30-60 characters
- **Description Length**: Optimal 120-160 characters  
- **Structured Data**: JSON-LD validation and count
- **Open Graph**: Complete OG tag coverage
- **Performance**: Core Web Vitals integration

### Build Integration

Automatic sitemap generation:

```bash
# Development
npm run build:sitemap:dev

# Production  
npm run build:sitemap

# With validation
npm run seo:validate
```

## 🌐 Production Deployment

### Generated Files

The system automatically generates:

- **`/public/sitemap.xml`**: Complete XML sitemap
- **`/public/robots.txt`**: SEO-optimized robots file
- **`/public/seo-report.json`**: Comprehensive SEO audit

### Robots.txt Configuration

```txt
User-agent: *
Allow: /
Allow: /auth/

# Block private areas
Disallow: /app/
Disallow: /api/
Disallow: /admin/

Sitemap: https://real2.ai/sitemap.xml
```

## 🔍 SEO Best Practices Implemented

### Technical SEO
- ✅ Unique titles for every page (30-60 chars)
- ✅ Meta descriptions under 160 characters
- ✅ Canonical URLs for all pages
- ✅ Open Graph and Twitter Card integration
- ✅ JSON-LD structured data
- ✅ Proper robots.txt and sitemap.xml
- ✅ hreflang for internationalization support

### Content SEO
- ✅ Dynamic title generation based on content
- ✅ Context-aware meta descriptions
- ✅ Breadcrumb structured data
- ✅ Article schema for analysis pages
- ✅ Property schema for real estate content

### Performance SEO
- ✅ React 19 compatible (no heavy dependencies)
- ✅ Minimal bundle impact
- ✅ Efficient DOM updates
- ✅ Core Web Vitals monitoring
- ✅ Development performance tracking

## 📈 Success Criteria

The SEO system achieves all requested requirements:

- ✅ **Unique, descriptive titles** for every page
- ✅ **Meta descriptions under 160 characters** with target keywords
- ✅ **Proper structured data validation** in Google Rich Results Test
- ✅ **Dynamic updates without page refresh**
- ✅ **SEO-friendly URL patterns**
- ✅ **Route-specific implementations** for all pages
- ✅ **Enhanced features**: breadcrumbs, articles, organization data
- ✅ **Integration**: All existing pages updated
- ✅ **Canonical URLs** prevent duplicate content
- ✅ **hreflang tags** ready for internationalization

## 🚀 Usage Examples

See `/src/examples/seoUsage.tsx` for comprehensive usage patterns and real-world examples.

---

**Built with ❤️ for Real2AI - Making Australian Real Estate Smarter with AI**
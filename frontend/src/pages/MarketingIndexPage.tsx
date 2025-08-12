import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion, useInView } from "framer-motion";
import {
  Shield,
  Clock,
  MapPin,
  TrendingUp,
  CheckCircle,
  Star,
  ArrowRight,
  Play,
  FileText,
  Brain,
  Target,
} from "lucide-react";

import { SEOHead } from "../components/seo/SEOHead";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { useSEO } from "../hooks/useSEO";

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  delay?: number;
}

const FeatureCard: React.FC<FeatureCardProps> = ({
  icon,
  title,
  description,
  delay = 0,
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5, delay }}
    viewport={{ once: true }}
    className="bg-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-shadow duration-300"
  >
    <div className="flex items-center mb-4">
      <div className="flex-shrink-0 w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600">
        {icon}
      </div>
      <h3 className="ml-4 text-lg font-semibold text-gray-900">{title}</h3>
    </div>
    <p className="text-gray-600 leading-relaxed">{description}</p>
  </motion.div>
);

interface TestimonialProps {
  quote: string;
  author: string;
  role: string;
  location: string;
  rating: number;
}

const Testimonial: React.FC<TestimonialProps> = ({
  quote,
  author,
  role,
  location,
  rating,
}) => (
  <Card className="p-6 bg-white">
    <div className="flex items-center mb-4">
      {Array.from({ length: rating }, (_, i) => (
        <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
      ))}
    </div>
    <blockquote className="text-gray-700 mb-4 italic">"{quote}"</blockquote>
    <div className="flex items-center">
      <div>
        <div className="font-semibold text-gray-900">{author}</div>
        <div className="text-sm text-gray-500">
          {role} • {location}
        </div>
      </div>
    </div>
  </Card>
);

const MarketingIndexPage: React.FC = () => {
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const heroRef = React.useRef<HTMLDivElement>(null);
  const isHeroInView = useInView(heroRef, { once: true });

  const statistics = [
    {
      number: "95%+",
      label: "Contract Accuracy",
      description: "Risk identification rate",
    },
    {
      number: "3 min",
      label: "Analysis Time",
      description: "Average processing time",
    },
    {
      number: "8 States",
      label: "Coverage",
      description: "All Australian states",
    },
    {
      number: "10,000+",
      label: "Contracts",
      description: "Successfully analyzed",
    },
  ];

  const features = [
    {
      icon: <Shield className="w-6 h-6" />,
      title: "AI-Powered Risk Detection",
      description:
        "Advanced GPT-4 and Gemini 2.5 Pro analysis identifies hidden risks, compliance issues, and unfavorable terms with 95%+ accuracy.",
    },
    {
      icon: <Clock className="w-6 h-6" />,
      title: "Instant Analysis",
      description:
        "Get comprehensive contract analysis in minutes, not days. Real-time progress tracking keeps you informed throughout the process.",
    },
    {
      icon: <MapPin className="w-6 h-6" />,
      title: "Australian Legal Expertise",
      description:
        "Built specifically for Australian property laws. Covers NSW, VIC, QLD, SA, WA, TAS, NT, ACT with state-specific compliance validation.",
    },
    {
      icon: <TrendingUp className="w-6 h-6" />,
      title: "Market Intelligence",
      description:
        "Integrated with Domain.com.au and CoreLogic for real-time property valuations and market insights to inform your decisions.",
    },
    {
      icon: <FileText className="w-6 h-6" />,
      title: "OCR Technology",
      description:
        "Advanced document scanning and text extraction handles any contract format - scanned PDFs, images, or digital documents.",
    },
    {
      icon: <Brain className="w-6 h-6" />,
      title: "Multi-Agent AI",
      description:
        "LangGraph workflow system with specialized AI agents for contract terms, compliance, risk assessment, and recommendations.",
    },
  ];

  const testimonials = [
    {
      quote:
        "Real2.AI saved me from a terrible contract with hidden clauses. The AI caught issues my lawyer missed initially.",
      author: "Sarah Chen",
      role: "First-time Buyer",
      location: "Sydney, NSW",
      rating: 5,
    },
    {
      quote:
        "As a buyer's agent, this tool has become essential. It helps me provide better service to my clients with instant analysis.",
      author: "Michael Thompson",
      role: "Buyer's Agent",
      location: "Melbourne, VIC",
      rating: 5,
    },
    {
      quote:
        "The compliance checking for Queensland regulations is spot-on. Gives me confidence in every property purchase.",
      author: "Emma Rodriguez",
      role: "Property Investor",
      location: "Brisbane, QLD",
      rating: 5,
    },
  ];

  const faqItems = [
    {
      question: "How accurate is Real2.AI's contract analysis?",
      answer:
        "Real2.AI achieves 95%+ accuracy in identifying contract risks, compliance issues, and unfavorable terms through our advanced AI models including GPT-4 and Gemini 2.5 Pro, specifically trained on Australian property law.",
    },
    {
      question: "Which Australian states are supported?",
      answer:
        "Real2.AI supports all Australian states and territories: NSW, VIC, QLD, SA, WA, TAS, NT, and ACT. Our AI is trained on state-specific property laws and regulations.",
    },
    {
      question: "How long does contract analysis take?",
      answer:
        "Most contracts are analyzed within 2-5 minutes. Complex documents may take up to 10 minutes. You'll receive real-time progress updates throughout the process.",
    },
    {
      question: "Is my contract data secure?",
      answer:
        "Yes, we use enterprise-grade security with end-to-end encryption. Your documents are processed securely and automatically deleted after analysis unless you choose to save them.",
    },
    {
      question: "Can Real2.AI replace my conveyancer or lawyer?",
      answer:
        "Real2.AI is designed to complement, not replace, professional legal advice. Our AI analysis helps you identify potential issues early and have more informed discussions with your legal team.",
    },
  ];

  // Build structured data using existing page content
  const structuredData = [
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: "Real2.AI",
      applicationCategory: "Real Estate AI Assistant",
      operatingSystem: "Web Browser",
      offers: {
        "@type": "Offer",
        price: "49",
        priceCurrency: "AUD",
      },
      aggregateRating: {
        "@type": "AggregateRating",
        ratingValue: "4.8",
        reviewCount: "247",
      },
    },
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqItems.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: item.answer,
        },
      })),
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Home",
          item: "https://real2.ai/",
        },
      ],
    },
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "Real2.AI",
      url: "https://real2.ai",
      logo: "https://real2.ai/logo.png",
    },
  ];

  // SEO optimization
  const { seoData } = useSEO({
    title:
      "Real2.AI - AI-Powered Australian Real Estate Contract Analysis | Your AI Step Before The Deal",
    description:
      "Real2.AI provides intelligent Australian real estate contract analysis with 95%+ accuracy. State-specific compliance checking, instant risk assessment, and comprehensive property intelligence for NSW, VIC, QLD. Start your free analysis today.",
    keywords: [
      "Australian real estate AI",
      "contract analysis Australia",
      "property risk assessment",
      "NSW VIC QLD contract review",
      "AI property assistant",
      "real estate compliance check",
      "Australian property laws",
      "contract AI analysis",
      "property purchase protection",
    ],
    canonical: "/",
    structuredData,
  });

  return (
    <>
      <SEOHead data={seoData} />
      <main
        role="main"
        className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50"
      >
        {/* Hero Section */}
        <section
          id="hero"
          ref={heroRef}
          className="relative overflow-hidden py-20 lg:py-32"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 to-indigo-600/10"></div>
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isHeroInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6 }}
                className="mb-8"
              >
                <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
                  Your{" "}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                    AI Step
                  </span>{" "}
                  Before the Deal
                </h1>
                <p className="text-xl lg:text-2xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
                  Australia's most advanced AI real estate assistant. Analyze
                  contracts, assess risks, and make confident property decisions
                  with 95%+ accuracy.
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isHeroInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12"
              >
                <Link to="/register">
                  <Button
                    size="lg"
                    className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 text-lg"
                  >
                    Start Free Analysis
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </Link>
                <button
                  onClick={() => setIsVideoPlaying(true)}
                  className="flex items-center text-gray-700 hover:text-blue-600 transition-colors"
                >
                  <div className="w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center mr-3">
                    <Play className="w-5 h-5 text-blue-600 ml-1" />
                  </div>
                  Watch 2-min Demo
                </button>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={isHeroInView ? { opacity: 1, scale: 1 } : {}}
                transition={{ duration: 0.8, delay: 0.4 }}
                className="relative max-w-4xl mx-auto"
              >
                <img
                  src="/api/placeholder/800/500"
                  alt="Real2.AI Dashboard showing contract analysis interface"
                  className="w-full rounded-2xl shadow-2xl"
                  width={800}
                  height={500}
                  loading="eager"
                  decoding="async"
                  fetchPriority="high"
                  sizes="(max-width: 1024px) 100vw, 800px"
                />
                <div className="absolute -bottom-6 -left-6 bg-white rounded-lg shadow-lg p-4 flex items-center">
                  <CheckCircle className="w-6 h-6 text-green-500 mr-2" />
                  <span className="text-sm font-medium">
                    95%+ Accuracy Rate
                  </span>
                </div>
                <div className="absolute -top-6 -right-6 bg-white rounded-lg shadow-lg p-4 flex items-center">
                  <Clock className="w-6 h-6 text-blue-500 mr-2" />
                  <span className="text-sm font-medium">3-minute Analysis</span>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Trust & Social Proof */}
        <section id="social-proof" className="py-16 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <p className="text-gray-600 mb-8">
                Trusted by thousands of Australian property buyers and
                professionals
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                {statistics.map((stat, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    viewport={{ once: true }}
                    className="text-center"
                  >
                    <div className="text-3xl lg:text-4xl font-bold text-blue-600 mb-2">
                      {stat.number}
                    </div>
                    <div className="text-lg font-semibold text-gray-900 mb-1">
                      {stat.label}
                    </div>
                    <div className="text-sm text-gray-500">
                      {stat.description}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Key Benefits */}
        <section id="benefits" className="py-20 bg-gray-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                viewport={{ once: true }}
              >
                <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                  Why Choose Real2.AI?
                </h2>
                <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                  Advanced AI technology meets Australian real estate expertise
                  to protect your property investments
                </p>
              </motion.div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {features.map((feature, index) => (
                <FeatureCard
                  key={index}
                  icon={feature.icon}
                  title={feature.title}
                  description={feature.description}
                  delay={index * 0.1}
                />
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="py-20 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                How It Works
              </h2>
              <p className="text-xl text-gray-600">
                Get professional-grade contract analysis in three simple steps
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
              {[
                {
                  step: "1",
                  title: "Upload Contract",
                  description:
                    "Simply upload your contract or document. We support PDF, DOC, DOCX, and even scanned images.",
                  icon: <FileText className="w-8 h-8" />,
                },
                {
                  step: "2",
                  title: "AI Analysis",
                  description:
                    "Our multi-agent AI system analyzes every clause, checks compliance, and identifies potential risks.",
                  icon: <Brain className="w-8 h-8" />,
                },
                {
                  step: "3",
                  title: "Receive Report",
                  description:
                    "Get a comprehensive analysis report with risk scores, recommendations, and next steps.",
                  icon: <Target className="w-8 h-8" />,
                },
              ].map((step, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.2 }}
                  viewport={{ once: true }}
                  className="text-center relative"
                >
                  <div className="mb-6">
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 mx-auto mb-4">
                      {step.icon}
                    </div>
                    <div className="absolute -top-2 -right-2 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                      {step.step}
                    </div>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    {step.title}
                  </h3>
                  <p className="text-gray-600">{step.description}</p>
                  {index < 2 && (
                    <div className="hidden md:block absolute top-8 -right-6 w-12 h-0.5 bg-blue-200"></div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Testimonials */}
        <section id="testimonials" className="py-20 bg-gray-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                What Our Users Say
              </h2>
              <p className="text-xl text-gray-600">
                Join thousands of satisfied property buyers across Australia
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {testimonials.map((testimonial, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  viewport={{ once: true }}
                >
                  <Testimonial {...testimonial} />
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Australian Focus */}
        <section id="australian-market" className="py-20 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6 }}
                viewport={{ once: true }}
              >
                <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-6">
                  Built for the Australian Market
                </h2>
                <p className="text-xl text-gray-600 mb-8">
                  Real2.AI understands the unique complexities of Australian
                  property law, from stamp duty calculations to cooling-off
                  periods across all states.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    "NSW Property Law",
                    "VIC Regulations",
                    "QLD Compliance",
                    "SA Requirements",
                    "WA Standards",
                    "TAS Guidelines",
                    "NT Rules",
                    "ACT Protocols",
                  ].map((item, index) => (
                    <div key={index} className="flex items-center">
                      <CheckCircle className="w-5 h-5 text-green-500 mr-3" />
                      <span className="text-gray-700">{item}</span>
                    </div>
                  ))}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6 }}
                viewport={{ once: true }}
                className="relative"
              >
                <img
                  src="/api/placeholder/600/400"
                  alt="Map of Australia showing state coverage"
                  className="w-full rounded-2xl shadow-lg"
                  width={600}
                  height={400}
                  loading="lazy"
                  decoding="async"
                  sizes="(max-width: 1024px) 100vw, 600px"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-blue-900/20 to-transparent rounded-2xl"></div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Vision Section */}
        <section id="vision" className="py-20 bg-white">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-6">
              Our Vision
            </h2>
            <p className="text-xl text-gray-600 mb-10 max-w-3xl mx-auto">
              Empower every Australian property buyer with trustworthy AI that
              makes complex contracts clear, reduces risk, and levels the
              playing field—so great property decisions are fast, fair, and
              accessible.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
              {[
                {
                  title: "Trust First",
                  desc: "Transparent AI explanations and state-specific compliance checks you can rely on.",
                },
                {
                  title: "Speed with Substance",
                  desc: "Instant analysis without sacrificing depth—actionable insights in minutes.",
                },
                {
                  title: "Access for All",
                  desc: "Professional-grade diligence at an accessible price, across all Australian states.",
                },
              ].map((item, i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl p-6 shadow-md border border-gray-100"
                >
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-gray-600 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section id="faq" className="py-20 bg-gray-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                Frequently Asked Questions
              </h2>
              <p className="text-xl text-gray-600">
                Everything you need to know about Real2.AI
              </p>
            </div>

            <div className="space-y-6">
              {faqItems.map((item, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  viewport={{ once: true }}
                  className="bg-white rounded-lg shadow-md"
                >
                  <details className="p-6">
                    <summary className="text-lg font-semibold text-gray-900 cursor-pointer hover:text-blue-600 transition-colors">
                      {item.question}
                    </summary>
                    <div className="mt-4 text-gray-600 leading-relaxed">
                      {item.answer}
                    </div>
                  </details>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section
          id="get-started"
          className="py-20 bg-gradient-to-r from-blue-600 to-indigo-700"
        >
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              viewport={{ once: true }}
            >
              <h2 className="text-3xl lg:text-4xl font-bold text-white mb-6">
                Ready to Make Smarter Property Decisions?
              </h2>
              <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
                Join thousands of Australian property buyers who trust Real2.AI
                to protect their investments.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                <Link to="/register">
                  <Button
                    size="lg"
                    className="w-full sm:w-auto bg-white text-blue-600 hover:bg-gray-50 px-8 py-3 text-lg"
                  >
                    Start Your Free Analysis
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </Link>
                <Link
                  to="/demo"
                  className="text-blue-100 hover:text-white underline"
                >
                  Book a Personal Demo
                </Link>
              </div>
              <p className="text-sm text-blue-200 mt-6">
                No credit card required • 30-day money-back guarantee •
                Enterprise support available
              </p>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Video Modal */}
      {isVideoPlaying && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="relative max-w-4xl w-full mx-4">
            <button
              onClick={() => setIsVideoPlaying(false)}
              className="absolute -top-12 right-0 text-white text-2xl hover:text-gray-300"
              aria-label="Close demo video"
            >
              ×
            </button>
            <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden">
              <iframe
                src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&modestbranding=1&rel=0"
                className="w-full h-full"
                allow="autoplay; encrypted-media"
                allowFullScreen
                title="Real2.AI demo video"
              ></iframe>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default MarketingIndexPage;

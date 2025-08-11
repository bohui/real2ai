"""
Example usage of CoreLogic API client for Real2.AI platform.

This file demonstrates the main features and capabilities of the CoreLogic client,
including valuations, market analytics, risk assessment, and cost management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from .client import CoreLogicClient
from .config import CoreLogicClientConfig
from .settings import create_corelogic_client_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_valuation():
    """Example: Basic property valuation using AVM."""
    print("\n=== Basic Property Valuation Example ===")
    
    # Create client configuration
    config = CoreLogicClientConfig(
        api_key="your_api_key_here",
        client_id="your_client_id_here",
        client_secret="your_client_secret_here",
        environment="sandbox",
        service_tier="professional"
    )
    
    async with CoreLogicClient(config) as client:
        try:
            # Get AVM valuation for a property
            valuation = await client.get_property_valuation(
                address="123 Collins Street, Melbourne VIC 3000",
                property_details={
                    "valuation_type": "avm",
                    "property_type": "apartment",
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "building_area": 85
                }
            )
            
            print(f"Valuation Amount: ${valuation['valuation_amount']:,}")
            print(f"Confidence Score: {valuation['confidence_score']:.2f}")
            print(f"Valuation Type: {valuation['valuation_type']}")
            print(f"Value Range: ${valuation['value_range']['low']:,} - ${valuation['value_range']['high']:,}")
            
        except Exception as e:
            logger.error(f"Valuation failed: {e}")


async def example_comprehensive_property_analysis():
    """Example: Comprehensive property analysis combining multiple data sources."""
    print("\n=== Comprehensive Property Analysis Example ===")
    
    config = create_corelogic_client_config()  # Load from environment
    
    async with CoreLogicClient(config) as client:
        property_address = "456 Sydney Road, Brunswick VIC 3056"
        
        try:
            # 1. Get property details
            print("1. Getting property details...")
            property_details = await client.get_property_details("property_123")
            
            # 2. Get valuation
            print("2. Getting valuation...")
            valuation = await client.get_property_valuation(
                address=property_address,
                property_details={
                    "valuation_type": "desktop",
                    "property_type": "house",
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "land_area": 450
                }
            )
            
            # 3. Get comparable sales
            print("3. Getting comparable sales...")
            comparables = await client.get_comparable_sales("property_123", radius_km=1.5)
            
            # 4. Get market analytics
            print("4. Getting market analytics...")
            market_data = await client.get_market_analytics(
                location={"suburb": "Brunswick", "state": "VIC"},
                property_type="house"
            )
            
            # 5. Get risk assessment
            print("5. Getting risk assessment...")
            risk_assessment = await client.get_property_risk_assessment("property_123")
            
            # 6. Calculate investment yield
            print("6. Calculating investment yield...")
            yield_analysis = await client.calculate_investment_yield(
                property_id="property_123",
                purchase_price=valuation["valuation_amount"],
                rental_income=520 * 52  # $520/week
            )
            
            # Compile comprehensive report
            comprehensive_report = {
                "property_address": property_address,
                "analysis_date": datetime.now().isoformat(),
                "valuation": {
                    "estimated_value": valuation["valuation_amount"],
                    "confidence": valuation["confidence_score"],
                    "method": valuation["valuation_type"]
                },
                "market_context": {
                    "suburb_median": market_data["market_metrics"]["median_price"],
                    "growth_1yr": market_data["market_metrics"]["price_growth_1yr"],
                    "days_on_market": market_data["market_metrics"]["days_on_market"]
                },
                "comparables": {
                    "count": comparables["comparable_count"],
                    "median_price": comparables["analysis_summary"]["median_price"]
                },
                "risk_profile": {
                    "overall_score": risk_assessment["overall_risk_score"],
                    "risk_level": risk_assessment["risk_level"]
                },
                "investment_metrics": {
                    "gross_yield": yield_analysis["gross_yield"],
                    "net_yield": yield_analysis["net_yield"],
                    "cash_flow": yield_analysis["cash_flow"]
                }
            }
            
            print("\n--- Comprehensive Analysis Results ---")
            print(f"Property: {comprehensive_report['property_address']}")
            print(f"Estimated Value: ${comprehensive_report['valuation']['estimated_value']:,}")
            print(f"Confidence: {comprehensive_report['valuation']['confidence']:.2f}")
            print(f"Suburb Median: ${comprehensive_report['market_context']['suburb_median']:,}")
            print(f"1-Year Growth: {comprehensive_report['market_context']['growth_1yr']:.1f}%")
            print(f"Risk Level: {comprehensive_report['risk_profile']['risk_level']}")
            print(f"Gross Yield: {comprehensive_report['investment_metrics']['gross_yield']:.2f}%")
            
        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {e}")


async def example_bulk_valuation():
    """Example: Bulk valuation for multiple properties."""
    print("\n=== Bulk Valuation Example ===")
    
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        # List of addresses to value
        addresses = [
            "123 Smith Street, Collingwood VIC 3066",
            "456 Jones Avenue, Richmond VIC 3121",
            "789 Brown Road, Hawthorn VIC 3122",
            "321 Green Street, Fitzroy VIC 3065",
            "654 Blue Crescent, Carlton VIC 3053"
        ]
        
        try:
            print(f"Performing bulk valuation for {len(addresses)} properties...")
            
            # Perform bulk AVM valuation
            bulk_results = await client.bulk_valuation(addresses, "avm")
            
            # Process results
            successful_valuations = [r for r in bulk_results if r.get("status") == "success"]
            failed_valuations = [r for r in bulk_results if r.get("status") != "success"]
            
            print(f"\nResults: {len(successful_valuations)} successful, {len(failed_valuations)} failed")
            
            # Display successful valuations
            total_value = 0
            for result in successful_valuations:
                value = result["valuation_amount"]
                confidence = result["confidence_score"]
                print(f"  {result['address']}: ${value:,} (confidence: {confidence:.2f})")
                total_value += value
            
            if successful_valuations:
                average_value = total_value / len(successful_valuations)
                print(f"\nAverage valuation: ${average_value:,}")
            
            # Display failed valuations
            if failed_valuations:
                print("\nFailed valuations:")
                for result in failed_valuations:
                    print(f"  {result['address']}: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"Bulk valuation failed: {e}")


async def example_market_research():
    """Example: Market research and analytics."""
    print("\n=== Market Research Example ===")
    
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        suburbs_to_analyze = [
            {"suburb": "Toorak", "state": "VIC"},
            {"suburb": "Richmond", "state": "VIC"},
            {"suburb": "Carlton", "state": "VIC"},
            {"suburb": "St Kilda", "state": "VIC"}
        ]
        
        market_comparison = []
        
        for location in suburbs_to_analyze:
            try:
                print(f"Analyzing {location['suburb']}, {location['state']}...")
                
                # Get market analytics
                market_data = await client.get_market_analytics(location, "house")
                
                # Get demographics
                demographics = await client.get_suburb_demographics(
                    location["suburb"], 
                    location["state"]
                )
                
                suburb_analysis = {
                    "location": f"{location['suburb']}, {location['state']}",
                    "median_price": market_data["market_metrics"]["median_price"],
                    "growth_1yr": market_data["market_metrics"]["price_growth_1yr"],
                    "growth_5yr": market_data["market_metrics"]["price_growth_5yr"],
                    "sales_volume": market_data["market_metrics"]["sales_volume"],
                    "days_on_market": market_data["market_metrics"]["days_on_market"],
                    "population": demographics["population"].get("total", "N/A"),
                    "data_confidence": market_data["data_quality"]["confidence"]
                }
                
                market_comparison.append(suburb_analysis)
                
            except Exception as e:
                logger.error(f"Failed to analyze {location['suburb']}: {e}")
        
        # Display comparison results
        if market_comparison:
            print("\n--- Market Comparison Results ---")
            print(f"{'Suburb':<15} {'Median Price':<12} {'1yr Growth':<10} {'5yr Growth':<10} {'DOM':<5} {'Confidence':<10}")
            print("-" * 75)
            
            for suburb in sorted(market_comparison, key=lambda x: x["median_price"], reverse=True):
                print(f"{suburb['location']:<15} "
                      f"${suburb['median_price']:>10,} "
                      f"{suburb['growth_1yr']:>8.1f}% "
                      f"{suburb['growth_5yr']:>8.1f}% "
                      f"{suburb['days_on_market']:>3} "
                      f"{suburb['data_confidence']:>8.2f}")


async def example_cost_management():
    """Example: Cost tracking and budget management."""
    print("\n=== Cost Management Example ===")
    
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        try:
            # Check initial cost status
            print("1. Initial cost status:")
            cost_summary = await client.get_cost_summary()
            print(f"   Daily cost: ${cost_summary['daily_cost']:.2f}")
            print(f"   Monthly cost: ${cost_summary['monthly_cost']:.2f}")
            print(f"   Total requests: {cost_summary['total_requests']}")
            
            # Perform some API operations
            print("\n2. Performing API operations...")
            
            # Get a valuation (costs money)
            valuation = await client.get_property_valuation(
                "123 Test Street, Sydney NSW 2000",
                {"valuation_type": "avm"}
            )
            print(f"   Valuation completed: ${valuation['valuation_amount']:,}")
            
            # Get market analytics (costs less)
            market_data = await client.get_market_analytics(
                {"suburb": "Sydney", "state": "NSW"}
            )
            print(f"   Market analytics completed")
            
            # Check updated cost status
            print("\n3. Updated cost status:")
            updated_cost_summary = await client.get_cost_summary()
            print(f"   Daily cost: ${updated_cost_summary['daily_cost']:.2f}")
            print(f"   Cost increase: ${updated_cost_summary['daily_cost'] - cost_summary['daily_cost']:.2f}")
            print(f"   Budget utilization: {updated_cost_summary['budget_utilization']['daily_percentage']:.1f}%")
            
            # Show operation breakdown
            if updated_cost_summary.get('operation_breakdown'):
                print("\n4. Operation cost breakdown:")
                for operation, cost in updated_cost_summary['operation_breakdown']['costs'].items():
                    count = updated_cost_summary['operation_breakdown']['counts'].get(operation, 0)
                    print(f"   {operation}: {count} requests, ${cost:.2f}")
            
        except Exception as e:
            logger.error(f"Cost management example failed: {e}")


async def example_risk_assessment():
    """Example: Comprehensive risk assessment."""
    print("\n=== Risk Assessment Example ===")
    
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        properties_to_assess = [
            "property_high_risk",
            "property_medium_risk", 
            "property_low_risk"
        ]
        
        risk_assessments = []
        
        for property_id in properties_to_assess:
            try:
                print(f"Assessing risk for {property_id}...")
                
                risk_data = await client.get_property_risk_assessment(
                    property_id,
                    assessment_type="comprehensive"
                )
                
                risk_summary = {
                    "property_id": property_id,
                    "overall_risk_score": risk_data["overall_risk_score"],
                    "risk_level": risk_data["risk_level"],
                    "market_risk": risk_data["risk_factors"]["market_risk"].get("score", 0),
                    "environmental_risk": risk_data["risk_factors"]["environmental_risk"].get("score", 0),
                    "structural_risk": risk_data["risk_factors"]["structural_risk"].get("score", 0),
                    "location_risk": risk_data["risk_factors"]["location_risk"].get("score", 0),
                    "recommendations": len(risk_data["recommendations"])
                }
                
                risk_assessments.append(risk_summary)
                
            except Exception as e:
                logger.error(f"Risk assessment failed for {property_id}: {e}")
        
        # Display risk comparison
        if risk_assessments:
            print("\n--- Risk Assessment Results ---")
            print(f"{'Property':<20} {'Overall Risk':<12} {'Risk Level':<10} {'Market':<7} {'Environ':<8} {'Struct':<7} {'Location'}<8} {'Recom':<5}")
            print("-" * 85)
            
            for assessment in sorted(risk_assessments, key=lambda x: x["overall_risk_score"], reverse=True):
                print(f"{assessment['property_id']:<20} "
                      f"{assessment['overall_risk_score']:<12.2f} "
                      f"{assessment['risk_level']:<10} "
                      f"{assessment['market_risk']:<7.2f} "
                      f"{assessment['environmental_risk']:<8.2f} "
                      f"{assessment['structural_risk']:<7.2f} "
                      f"{assessment['location_risk']:<8.2f} "
                      f"{assessment['recommendations']:<5}")


async def example_api_health_monitoring():
    """Example: API health and performance monitoring."""
    print("\n=== API Health Monitoring Example ===")
    
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        try:
            # Check API health
            health_status = await client.check_api_health()
            
            print("API Health Status:")
            print(f"  Status: {health_status['status']}")
            print(f"  Service Tier: {health_status['service_tier']}")
            print(f"  Environment: {health_status['environment']}")
            
            # Display rate limits
            rate_limits = health_status.get('rate_limits', {})
            print(f"\nRate Limits:")
            print(f"  Hourly: {rate_limits.get('hourly_requests_used', 0)}/{rate_limits.get('hourly_requests_limit', 0)}")
            print(f"  Per Second: {rate_limits.get('requests_per_second_used', 0)}/{rate_limits.get('requests_per_second_limit', 0)}")
            print(f"  Circuit Breaker: {'Open' if rate_limits.get('circuit_breaker_open') else 'Closed'}")
            
            # Display cost summary
            cost_summary = health_status.get('cost_summary', {})
            print(f"\nCost Summary:")
            print(f"  Daily Cost: ${cost_summary.get('daily_cost', 0):.2f}")
            print(f"  Monthly Cost: ${cost_summary.get('monthly_cost', 0):.2f}")
            print(f"  Total Requests: {cost_summary.get('total_requests', 0)}")
            print(f"  Valuations: {cost_summary.get('valuation_count', 0)}")
            
        except Exception as e:
            logger.error(f"Health monitoring failed: {e}")


async def main():
    """Run all examples."""
    print("CoreLogic API Client Examples")
    print("=" * 50)
    
    # Note: These examples require valid API credentials
    # Update the configuration with your actual credentials before running
    
    examples = [
        example_basic_valuation,
        example_comprehensive_property_analysis,
        example_bulk_valuation,
        example_market_research,
        example_cost_management,
        example_risk_assessment,
        example_api_health_monitoring
    ]
    
    for example_func in examples:
        try:
            await example_func()
            await asyncio.sleep(1)  # Brief pause between examples
        except Exception as e:
            logger.error(f"Example {example_func.__name__} failed: {e}")
        
        print("\n" + "="*50)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
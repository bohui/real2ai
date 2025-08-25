"""
Integration tests for the complete Property Profile system.

Tests the integration between Domain API, CoreLogic API, and the PropertyProfileService.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.services.property.property_profile_service import (
    PropertyProfileService,
    PropertyProfileRequest,
    get_property_profile_service,
)


class TestPropertyProfileIntegration:
    """Integration tests for property profile system."""

    @pytest.fixture
    async def mock_domain_client(self):
        """Mock Domain client with realistic responses."""
        client = AsyncMock()
        client.is_initialized = True

        # Mock property search
        client.search_properties = AsyncMock(
            return_value={
                "results": [
                    {
                        "id": "domain_property_123",
                        "address": "123 Collins Street, Melbourne VIC 3000",
                        "property_type": "apartment",
                        "bedrooms": 2,
                        "bathrooms": 1,
                        "parking_spaces": 1,
                        "building_area": 85,
                        "features": ["balcony", "gym", "concierge"],
                    }
                ]
            }
        )

        # Mock property details
        client.get_property_details = AsyncMock(
            return_value={
                "id": "domain_property_123",
                "address": "123 Collins Street, Melbourne VIC 3000",
                "property_type": "apartment",
                "bedrooms": 2,
                "bathrooms": 1,
                "parking_spaces": 1,
                "land_area": None,
                "building_area": 85,
                "features": ["balcony", "gym", "concierge"],
                "location": {"suburb": "Melbourne", "state": "VIC", "postcode": "3000"},
                "listing_date": "2024-07-15",
                "agent_details": {"name": "Test Agent", "agency": "Test Agency"},
            }
        )

        # Mock sales history
        client.get_sales_history = AsyncMock(
            return_value=[
                {
                    "sale_date": "2022-03-15",
                    "sale_price": 780000,
                    "sale_type": "private_sale",
                }
            ]
        )

        return client

    @pytest.fixture
    async def mock_corelogic_client(self):
        """Mock CoreLogic client with realistic responses."""
        client = AsyncMock()
        client.is_initialized = True

        # Mock property valuation
        client.get_property_valuation = AsyncMock(
            return_value={
                "valuation_amount": 850000,
                "valuation_type": "avm",
                "confidence_score": 0.85,
                "valuation_date": "2024-08-05",
                "methodology": "AVM",
                "comparables_used": 8,
                "value_range": {"low": 805000, "high": 895000},
                "market_conditions": "stable",
                "risk_factors": ["high_density_area"],
                "provider_metadata": {
                    "provider": "corelogic",
                    "report_id": "CL_20240805_123",
                    "cost": 5.00,
                },
            }
        )

        # Mock market analytics
        client.get_market_analytics = AsyncMock(
            return_value={
                "market_metrics": {
                    "median_price": 920000,
                    "price_growth_1yr": 8.5,
                    "price_growth_5yr": 45.2,
                    "days_on_market": 28,
                    "auction_clearance_rate": 0.75,
                },
                "market_trends": {
                    "trend_direction": "upward",
                    "trend_strength": "moderate",
                    "seasonal_factors": ["spring_peak"],
                },
                "suburb_insights": {
                    "demographics": {
                        "median_age": 34,
                        "household_size": 2.1,
                        "income_level": "high",
                    },
                    "amenities": ["public_transport", "shopping", "schools"],
                },
            }
        )

        # Mock risk assessment
        client.get_property_risk_assessment = AsyncMock(
            return_value={
                "overall_risk_score": 6.2,
                "risk_level": "medium",
                "risk_factors": [
                    {"factor": "market_volatility", "score": 7.0, "weight": 0.3},
                    {"factor": "location_risk", "score": 5.5, "weight": 0.25},
                    {"factor": "property_condition", "score": 4.0, "weight": 0.2},
                ],
                "mitigation_strategies": [
                    "diversify_portfolio",
                    "consider_insurance",
                    "monitor_market_conditions",
                ],
            }
        )

        # Mock investment yield calculation
        client.calculate_investment_yield = AsyncMock(
            return_value={
                "gross_yield": 4.2,
                "net_yield": 3.1,
                "rental_income": 2975,
                "expenses": {
                    "property_management": 148.75,
                    "insurance": 89.25,
                    "maintenance": 74.38,
                    "rates": 148.75,
                },
                "cash_flow": 2512.87,
            }
        )

        # Mock comparable sales
        client.get_comparable_sales = AsyncMock(
            return_value={
                "comparable_count": 6,
                "comparable_sales": [
                    {
                        "address": "125 Collins Street",
                        "sale_date": "2024-06-15",
                        "sale_price": 820000,
                        "property_type": "apartment",
                        "bedrooms": 2,
                        "bathrooms": 1,
                    },
                    {
                        "address": "127 Collins Street",
                        "sale_date": "2024-05-20",
                        "sale_price": 810000,
                        "property_type": "apartment",
                        "bedrooms": 2,
                        "bathrooms": 1,
                    },
                ],
                "statistics": {
                    "median_price": 815000,
                    "price_range": {"min": 780000, "max": 850000},
                    "days_on_market_avg": 25,
                },
            }
        )

        return client

    @pytest.fixture
    async def property_service(self):
        """Create property profile service for testing."""
        service = PropertyProfileService()
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_complete_property_profile_generation(
        self, property_service, mock_domain_client, mock_corelogic_client
    ):
        """Test complete property profile generation with all components."""

        # Mock the client factory to return our mock clients
        with (
            patch(
                "app.services.property_profile_service.get_domain_client",
                return_value=mock_domain_client,
            ),
            patch(
                "app.services.property_profile_service.get_corelogic_client",
                return_value=mock_corelogic_client,
            ),
        ):

            # Create request
            request = PropertyProfileRequest(
                address="123 Collins Street, Melbourne VIC 3000",
                valuation_type="avm",
                include_market_analysis=True,
                include_risk_assessment=True,
                include_investment_metrics=True,
                include_comparable_sales=True,
                radius_km=2.0,
            )

            # Generate profile
            profile = await property_service.generate_property_profile(request)

            # Verify response structure
            assert profile.request_id is not None
            assert profile.address == request.address
            assert profile.generated_at is not None
            assert "domain" in profile.data_sources
            assert "corelogic" in profile.data_sources

            # Verify property details from Domain
            assert profile.property_details["source"] == "domain"
            assert profile.property_details["property_type"] == "apartment"
            assert profile.property_details["bedrooms"] == 2
            assert profile.property_details["bathrooms"] == 1

            # Verify valuation data from CoreLogic
            assert profile.valuation_data["source"] == "corelogic"
            assert profile.valuation_data["valuation_amount"] == 850000
            assert profile.valuation_data["confidence_score"] == 0.85
            assert profile.valuation_data["valuation_type"] == "avm"

            # Verify market analysis
            assert profile.market_analysis is not None
            assert profile.market_analysis["market_metrics"]["median_price"] == 920000
            assert profile.market_analysis["market_metrics"]["price_growth_1yr"] == 8.5

            # Verify risk assessment
            assert profile.risk_assessment is not None
            assert profile.risk_assessment["overall_risk_score"] == 6.2
            assert profile.risk_assessment["risk_level"] == "medium"

            # Verify investment metrics
            assert profile.investment_metrics is not None
            assert profile.investment_metrics["gross_yield"] == 4.2
            assert profile.investment_metrics["net_yield"] == 3.1

            # Verify comparable sales
            assert profile.comparable_sales is not None
            assert profile.comparable_sales["comparable_count"] == 6

            # Verify data quality score calculation
            assert 0.0 <= profile.data_quality_score <= 1.0
            assert (
                profile.data_quality_score > 0.7
            )  # Should be high with good mock data

            # Verify cost calculation
            assert profile.total_cost > 0
            assert profile.processing_time_seconds > 0

            # Verify all client methods were called
            mock_domain_client.search_properties.assert_called_once()
            mock_domain_client.get_property_details.assert_called_once()
            mock_corelogic_client.get_property_valuation.assert_called_once()
            mock_corelogic_client.get_market_analytics.assert_called_once()
            mock_corelogic_client.get_property_risk_assessment.assert_called_once()
            mock_corelogic_client.calculate_investment_yield.assert_called_once()
            mock_corelogic_client.get_comparable_sales.assert_called_once()

    @pytest.mark.asyncio
    async def test_property_comparison(
        self, property_service, mock_domain_client, mock_corelogic_client
    ):
        """Test property comparison functionality."""

        # Mock different responses for different properties
        def domain_search_side_effect(params):
            address = params.get("address", "")
            if "Collins" in address:
                return {
                    "results": [
                        {
                            "id": "domain_property_123",
                            "address": address,
                            "property_type": "apartment",
                            "bedrooms": 2,
                            "bathrooms": 1,
                        }
                    ]
                }
            else:
                return {
                    "results": [
                        {
                            "id": "domain_property_456",
                            "address": address,
                            "property_type": "house",
                            "bedrooms": 3,
                            "bathrooms": 2,
                        }
                    ]
                }

        def corelogic_valuation_side_effect(address, property_details):
            if "Collins" in address:
                return {
                    "valuation_amount": 850000,
                    "valuation_type": "avm",
                    "confidence_score": 0.85,
                    "valuation_date": "2024-08-05",
                }
            else:
                return {
                    "valuation_amount": 1200000,
                    "valuation_type": "avm",
                    "confidence_score": 0.78,
                    "valuation_date": "2024-08-05",
                }

        mock_domain_client.search_properties.side_effect = domain_search_side_effect
        mock_corelogic_client.get_property_valuation.side_effect = (
            corelogic_valuation_side_effect
        )

        with (
            patch(
                "app.services.property_profile_service.get_domain_client",
                return_value=mock_domain_client,
            ),
            patch(
                "app.services.property_profile_service.get_corelogic_client",
                return_value=mock_corelogic_client,
            ),
        ):

            addresses = [
                "123 Collins Street, Melbourne VIC 3000",
                "456 Smith Street, Richmond VIC 3121",
            ]

            comparison = await property_service.compare_properties(
                addresses, ["valuation", "market_performance"]
            )

            # Verify comparison structure
            assert comparison["properties_compared"] == 2
            assert len(comparison["properties"]) == 2
            assert comparison["criteria"] == ["valuation", "market_performance"]

            # Verify property data
            properties = comparison["properties"]
            assert properties[0]["address"] == addresses[0]
            assert properties[1]["address"] == addresses[1]

            # Verify rankings
            rankings = comparison.get("rankings", {})
            assert "highest_valuation" in rankings

            # Verify summary statistics
            stats = comparison["summary_statistics"]
            assert "property_count" in stats
            assert stats["property_count"] == 2
            assert "valuation_statistics" in stats

    @pytest.mark.asyncio
    async def test_error_handling_property_not_found(
        self, property_service, mock_domain_client, mock_corelogic_client
    ):
        """Test error handling when property is not found."""

        # Mock Domain client to return no results
        mock_domain_client.search_properties = AsyncMock(return_value={"results": []})

        with (
            patch(
                "app.services.property_profile_service.get_domain_client",
                return_value=mock_domain_client,
            ),
            patch(
                "app.services.property_profile_service.get_corelogic_client",
                return_value=mock_corelogic_client,
            ),
        ):

            request = PropertyProfileRequest(
                address="999 Nonexistent Street, Unknown VIC 9999"
            )

            with pytest.raises(Exception):  # Should raise PropertyNotFoundError
                await property_service.generate_property_profile(request)

    @pytest.mark.asyncio
    async def test_partial_data_handling(
        self, property_service, mock_domain_client, mock_corelogic_client
    ):
        """Test handling of partial data when some services fail."""

        # Mock CoreLogic market analytics to fail
        mock_corelogic_client.get_market_analytics = AsyncMock(
            side_effect=Exception("Market data unavailable")
        )

        with (
            patch(
                "app.services.property_profile_service.get_domain_client",
                return_value=mock_domain_client,
            ),
            patch(
                "app.services.property_profile_service.get_corelogic_client",
                return_value=mock_corelogic_client,
            ),
        ):

            request = PropertyProfileRequest(
                address="123 Collins Street, Melbourne VIC 3000",
                include_market_analysis=True,
                include_risk_assessment=True,
            )

            profile = await property_service.generate_property_profile(request)

            # Should still succeed with partial data
            assert profile.request_id is not None
            assert profile.valuation_data["valuation_amount"] == 850000

            # Market analysis should be None or contain error
            assert profile.market_analysis is None or "error" in profile.market_analysis

            # Risk assessment should still work
            assert profile.risk_assessment is not None
            assert profile.risk_assessment["overall_risk_score"] == 6.2

            # Data quality score should be lower due to missing market data
            assert profile.data_quality_score < 1.0

    @pytest.mark.asyncio
    async def test_data_quality_scoring(self, property_service):
        """Test data quality scoring calculation."""

        # Create mock response with varying data completeness
        from app.services.property.property_profile_service import PropertyProfileResponse

        # High quality response
        high_quality_response = PropertyProfileResponse(
            request_id="test_123",
            address="123 Test Street",
            generated_at=datetime.now(timezone.utc),
            data_sources=["domain", "corelogic"],
            property_details={
                "address": "123 Test Street",
                "property_type": "house",
                "bedrooms": 3,
                "bathrooms": 2,
                "land_area": 600,
                "building_area": 180,
                "features": ["garage", "garden"],
            },
            valuation_data={"valuation_amount": 850000, "confidence_score": 0.92},
        )

        quality_score = property_service._calculate_data_quality_score(
            high_quality_response
        )
        assert quality_score > 0.6  # Should be reasonably high

        # Low quality response
        low_quality_response = PropertyProfileResponse(
            request_id="test_456",
            address="456 Test Street",
            generated_at=datetime.now(timezone.utc),
            data_sources=["domain"],
            property_details={
                "address": "456 Test Street",
                "property_type": "house",
                # Missing most details
            },
            valuation_data={
                "valuation_amount": 750000,
                "confidence_score": 0.45,  # Low confidence
            },
        )

        low_quality_score = property_service._calculate_data_quality_score(
            low_quality_response
        )
        assert low_quality_score < quality_score  # Should be lower
        assert low_quality_score >= 0.0  # Should not be negative

    @pytest.mark.asyncio
    async def test_service_singleton(self):
        """Test that the service singleton works correctly."""

        service1 = get_property_profile_service()
        service2 = get_property_profile_service()

        # Should be the same instance
        assert service1 is service2
        assert isinstance(service1, PropertyProfileService)

    @pytest.mark.asyncio
    async def test_cost_calculation(
        self, property_service, mock_domain_client, mock_corelogic_client
    ):
        """Test cost calculation for different request configurations."""

        with (
            patch(
                "app.services.property_profile_service.get_domain_client",
                return_value=mock_domain_client,
            ),
            patch(
                "app.services.property_profile_service.get_corelogic_client",
                return_value=mock_corelogic_client,
            ),
        ):

            # Basic AVM request
            basic_request = PropertyProfileRequest(
                address="123 Test Street",
                valuation_type="avm",
                include_market_analysis=False,
                include_risk_assessment=False,
                include_investment_metrics=False,
                include_comparable_sales=False,
            )

            basic_profile = await property_service.generate_property_profile(
                basic_request
            )
            basic_cost = basic_profile.total_cost

            # Full professional request
            premium_request = PropertyProfileRequest(
                address="123 Test Street",
                valuation_type="professional",
                include_market_analysis=True,
                include_risk_assessment=True,
                include_investment_metrics=True,
                include_comparable_sales=True,
            )

            premium_profile = await property_service.generate_property_profile(
                premium_request
            )
            premium_cost = premium_profile.total_cost

            # Premium should cost more than basic
            assert premium_cost > basic_cost
            assert basic_cost > 0
            assert premium_cost > 15  # Should be reasonably expensive for full analysis

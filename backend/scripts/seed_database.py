#!/usr/bin/env python3
"""
Database Seeding Script for Real2.AI
Populates the database with sample data for development and testing
"""

import os
import sys
import json
import logging
import asyncio
import argparse
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

import asyncpg
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid

# Add the app directory to the path so we can import from it
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.clients.factory import get_supabase_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """Seeds the Real2.AI database with sample data"""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.db_url = os.getenv("DATABASE_URL")

        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Missing required environment variables")

        # Database client will be initialized in the initialize method
        self.db_client = None

    async def initialize(self):
        """Initialize the database connection"""
        # Initialize the database client
        self.db_client = await get_supabase_client()

    async def get_db_connection(self):
        """Get direct database connection"""
        if not self.db_url:
            raise ValueError("DATABASE_URL not configured")
        return await asyncpg.connect(self.db_url)

    async def seed_demo_users(self):
        """Create demo user profiles for testing"""
        logger.info("Seeding demo users...")

        demo_users = [
            {
                "id": str(uuid.uuid4()),
                "email": "demo@real2.ai",
                "full_name": "Demo User",
                "phone_number": "+61 2 9876 5432",
                "australian_state": "NSW",
                "user_type": "investor",
                "subscription_status": "premium",
                "credits_remaining": 50,
                "organization": "Real2.AI Demo",
                "password": "1qa2ws#ED!@",
            },
            {
                "id": str(uuid.uuid4()),
                "email": "investor@real2.ai",
                "full_name": "Sarah Johnson",
                "phone_number": "+61 2 9876 5432",
                "australian_state": "NSW",
                "user_type": "investor",
                "subscription_status": "premium",
                "credits_remaining": 45,
                "organization": "Johnson Property Group",
                "password": "password123",
            },
            {
                "id": str(uuid.uuid4()),
                "email": "agent@real2.ai",
                "full_name": "Michael Chen",
                "phone_number": "+61 3 8765 4321",
                "australian_state": "VIC",
                "user_type": "agent",
                "subscription_status": "enterprise",
                "credits_remaining": 180,
                "organization": "Melbourne Premier Realty",
                "password": "password123",
            },
            {
                "id": str(uuid.uuid4()),
                "email": "buyer@real2.ai",
                "full_name": "Emma Thompson",
                "phone_number": "+61 7 7654 3210",
                "australian_state": "QLD",
                "user_type": "buyer",
                "subscription_status": "basic",
                "credits_remaining": 8,
                "organization": None,
                "password": "password123",
            },
        ]

        conn = await self.get_db_connection()
        try:
            created_users = []
            for user in demo_users:
                # First, check if user already exists in auth.users
                existing_user = await conn.fetchrow(
                    "SELECT id FROM auth.users WHERE email = $1", user["email"]
                )

                if existing_user:
                    # User already exists, use their ID
                    auth_user_id = existing_user["id"]
                    user["id"] = auth_user_id
                    logger.info(f"Found existing auth user: {user['email']}")
                else:
                    # Create user in Supabase auth
                    auth_user_id = None
                    try:
                        # Use Supabase client sign_up method (same as in main.py)
                        logger.info(
                            f"Attempting to create auth user for {user['email']}"
                        )

                        # Create user using the same method as the registration endpoint
                        user_result = self.db_client.auth.sign_up(
                            {
                                "email": user["email"],
                                "password": user["password"],
                                "options": {
                                    "data": {
                                        "australian_state": user["australian_state"],
                                        "user_type": user["user_type"],
                                        "full_name": user["full_name"],
                                    }
                                },
                            }
                        )

                        if user_result.user:
                            auth_user_id = user_result.user.id
                            user["id"] = auth_user_id
                            logger.info(
                                f"Created auth user: {user['email']} with ID: {auth_user_id}"
                            )
                        else:
                            raise Exception("User creation failed - no user returned")

                    except Exception as e:
                        logger.warning(
                            f"Failed to create auth user for {user['email']}: {e}"
                        )
                        logger.info(f"Error details: {type(e).__name__}: {str(e)}")
                        # Skip this user if auth creation fails
                        continue

                # Only create profile if auth user was created successfully or found
                if auth_user_id:
                    try:
                        # Check if profile already exists
                        existing_profile = await conn.fetchrow(
                            "SELECT id FROM profiles WHERE id = $1", user["id"]
                        )

                        if existing_profile:
                            logger.info(
                                f"Profile already exists for: {user['email']}, updating..."
                            )
                            await conn.execute(
                                """
                                UPDATE profiles 
                                SET email = $2,
                                    australian_state = $3,
                                    user_type = $4,
                                    subscription_status = $5,
                                    credits_remaining = $6
                                WHERE id = $1
                            """,
                                user["id"],
                                user["email"],
                                user["australian_state"],
                                user["user_type"],
                                user["subscription_status"],
                                user["credits_remaining"],
                            )
                            logger.info(f"Updated demo user profile: {user['email']}")
                            created_users.append(user)
                        else:
                            await conn.execute(
                                """
                                INSERT INTO profiles (id, email, australian_state, user_type, 
                                                    subscription_status, credits_remaining)
                                VALUES ($1, $2, $3, $4, $5, $6)
                                ON CONFLICT (id) DO UPDATE SET
                                    email = EXCLUDED.email,
                                    australian_state = EXCLUDED.australian_state,
                                    user_type = EXCLUDED.user_type,
                                    subscription_status = EXCLUDED.subscription_status,
                                    credits_remaining = EXCLUDED.credits_remaining
                            """,
                                user["id"],
                                user["email"],
                                user["australian_state"],
                                user["user_type"],
                                user["subscription_status"],
                                user["credits_remaining"],
                            )

                            logger.info(f"Created demo user profile: {user['email']}")
                            created_users.append(user)
                    except Exception as e:
                        logger.error(
                            f"Failed to create profile for {user['email']}: {e}"
                        )

        finally:
            await conn.close()

        return created_users

    async def seed_sample_documents(self, demo_users: List[Dict]):
        """Create sample document records"""
        logger.info("Seeding sample documents...")

        if not demo_users:
            logger.warning("No demo users available, skipping document seeding")
            return []

        # Ensure we have at least 4 users, or use the available ones
        available_users = demo_users[:4]  # Take up to 4 users
        if len(available_users) < 4:
            # If we have fewer than 4 users, repeat the last user to fill the slots
            while len(available_users) < 4:
                available_users.append(
                    available_users[-1] if available_users else demo_users[0]
                )

        sample_documents = [
            {
                "user_id": available_users[0]["id"],  # demo user
                "original_filename": "Demo_Contract_Analysis.pdf",
                "storage_path": f"{available_users[0]['id']}/2024/01/15/demo_contract_001.pdf",
                "file_type": "application/pdf",
                "file_size": 2048576,  # 2MB
                "processing_status": "processed",
            },
            {
                "user_id": available_users[0]["id"],  # demo user
                "original_filename": "Demo_Property_Contract.pdf",
                "storage_path": f"{available_users[0]['id']}/2024/01/20/demo_contract_002.pdf",
                "file_type": "application/pdf",
                "file_size": 3145728,  # 3MB
                "processing_status": "processed",
            },
            {
                "user_id": available_users[1]["id"],  # investor
                "original_filename": "Purchase_Agreement_Sydney_Unit.pdf",
                "storage_path": f"{available_users[1]['id']}/2024/01/15/contract_001.pdf",
                "file_type": "application/pdf",
                "file_size": 2048576,  # 2MB
                "processing_status": "processed",
            },
            {
                "user_id": available_users[1]["id"],  # investor
                "original_filename": "Off_Plan_Contract_Parramatta.pdf",
                "storage_path": f"{available_users[1]['id']}/2024/01/20/contract_002.pdf",
                "file_type": "application/pdf",
                "file_size": 3145728,  # 3MB
                "processing_status": "processed",
            },
            {
                "user_id": available_users[2]["id"],  # agent
                "original_filename": "Lease_Agreement_Melbourne_CBD.pdf",
                "storage_path": f"{available_users[2]['id']}/2024/01/18/lease_001.pdf",
                "file_type": "application/pdf",
                "file_size": 1572864,  # 1.5MB
                "processing_status": "processed",
            },
            {
                "user_id": available_users[3]["id"],  # buyer
                "original_filename": "House_Purchase_Brisbane.pdf",
                "storage_path": f"{available_users[3]['id']}/2024/01/25/house_001.pdf",
                "file_type": "application/pdf",
                "file_size": 2621440,  # 2.5MB
                "processing_status": "processed",
            },
        ]

        conn = await self.get_db_connection()
        try:
            document_ids = []
            for doc in sample_documents:
                try:
                    doc_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO documents (id, user_id, original_filename, storage_path, file_type, file_size, processing_status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (id) DO NOTHING
                    """,
                        doc_id,
                        doc["user_id"],
                        doc["original_filename"],
                        doc["storage_path"],
                        doc["file_type"],
                        doc["file_size"],
                        doc["processing_status"],
                    )

                    document_ids.append({**doc, "id": doc_id})
                    logger.info(f"Created sample document: {doc['original_filename']}")
                except Exception as e:
                    logger.error(
                        f"Failed to create document {doc['original_filename']}: {e}"
                    )

        finally:
            await conn.close()

        return document_ids

    async def seed_sample_contracts(self, documents: List[Dict]):
        """Create sample contract records"""
        logger.info("Seeding sample contracts...")

        contract_types = [
            "purchase_agreement",
            "off_plan",
            "lease_agreement",
            "purchase_agreement",
        ]

        conn = await self.get_db_connection()
        try:
            contract_ids = []
            for i, doc in enumerate(documents):
                contract_id = str(uuid.uuid4())
                contract_type = contract_types[i % len(contract_types)]

                # Determine state based on filename or user
                if (
                    "sydney" in doc["original_filename"].lower()
                    or "parramatta" in doc["original_filename"].lower()
                ):
                    state = "NSW"
                elif "melbourne" in doc["original_filename"].lower():
                    state = "VIC"
                elif "brisbane" in doc["original_filename"].lower():
                    state = "QLD"
                else:
                    state = "NSW"  # default

                # Generate content hash for shared contract (simplified for seeding)
                content_hash = hashlib.sha256(f"{contract_id}".encode()).hexdigest()

                await conn.execute(
                    """
                    INSERT INTO contracts (id, content_hash, contract_type, australian_state)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                """,
                    contract_id,
                    content_hash,
                    contract_type,
                    state,
                )

                # Create user_contract_views entry for user access
                await conn.execute(
                    """
                    INSERT INTO user_contract_views (user_id, content_hash, property_address, source)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                    """,
                    doc["user_id"],
                    content_hash,
                    None,  # property_address - could be added later
                    "upload",
                )

                contract_ids.append(
                    {
                        "id": contract_id,
                        "content_hash": content_hash,
                        "document_id": doc["id"],
                        "user_id": doc["user_id"],
                        "contract_type": contract_type,
                        "state": state,
                    }
                )
                logger.info(f"Created sample contract: {contract_type} in {state}")

        finally:
            await conn.close()

        return contract_ids

    async def seed_sample_analyses(self, contracts: List[Dict]):
        """Create sample contract analyses with realistic data"""
        logger.info("Seeding sample analyses...")

        sample_analyses = [
            {
                "executive_summary": {
                    "overall_risk_score": 3.2,
                    "confidence_level": 0.92,
                    "total_recommendations": 5,
                    "compliance_status": "compliant",
                    "key_findings": [
                        "Standard purchase agreement with fair terms",
                        "Appropriate cooling-off period included",
                        "Building inspection clause present",
                    ],
                },
                "risk_assessment": {
                    "risk_factors": [
                        {
                            "category": "Financial",
                            "risk": "Deposit forfeiture clause",
                            "severity": "medium",
                            "likelihood": "low",
                            "impact": "Contract includes standard 10% deposit with reasonable forfeiture terms",
                        },
                        {
                            "category": "Legal",
                            "risk": "Special conditions",
                            "severity": "low",
                            "likelihood": "low",
                            "impact": "Two minor special conditions that are standard for NSW purchases",
                        },
                    ]
                },
                "compliance_check": {
                    "compliance_issues": [],
                    "australian_standards_met": True,
                    "state_specific_requirements": [
                        "NSW Fair Trading compliance verified"
                    ],
                },
                "recommendations": [
                    {
                        "priority": "medium",
                        "category": "Due Diligence",
                        "recommendation": "Ensure building inspection is completed before settlement",
                        "australian_context": "NSW requires comprehensive building inspections for properties over 20 years old",
                    }
                ],
            },
            {
                "executive_summary": {
                    "overall_risk_score": 6.8,
                    "confidence_level": 0.87,
                    "total_recommendations": 8,
                    "compliance_status": "requires_attention",
                    "key_findings": [
                        "Off-plan purchase with extended sunset clause",
                        "Progress payment schedule requires review",
                        "Variation clause needs clarification",
                    ],
                },
                "risk_assessment": {
                    "risk_factors": [
                        {
                            "category": "Construction",
                            "risk": "Extended sunset clause (5 years)",
                            "severity": "high",
                            "likelihood": "medium",
                            "impact": "Developer has excessive time to complete, market risk for buyer",
                        },
                        {
                            "category": "Financial",
                            "risk": "Progressive payment structure",
                            "severity": "medium",
                            "likelihood": "high",
                            "impact": "Payments due before practical completion stages",
                        },
                    ]
                },
                "compliance_check": {
                    "compliance_issues": [
                        "Sunset clause exceeds recommended 2-year maximum",
                        "Progress payment schedule not aligned with construction milestones",
                    ],
                    "australian_standards_met": False,
                    "state_specific_requirements": [
                        "NSW Home Building Act compliance needs review"
                    ],
                },
            },
        ]

        conn = await self.get_db_connection()
        try:
            for i, contract in enumerate(contracts[:2]):  # Only seed first 2 contracts
                analysis_data = sample_analyses[i % len(sample_analyses)]

                analysis_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO contract_analyses (
                        id, content_hash, agent_version, status, 
                        executive_summary, risk_assessment, compliance_check, recommendations,
                        overall_risk_score, confidence_level, processing_time_seconds
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (content_hash) DO NOTHING
                """,
                    analysis_id,
                    contract["content_hash"],
                    "1.0",
                    "completed",
                    json.dumps(analysis_data["executive_summary"]),
                    json.dumps(analysis_data["risk_assessment"]),
                    json.dumps(analysis_data["compliance_check"]),
                    json.dumps(analysis_data.get("recommendations", [])),
                    analysis_data["executive_summary"]["overall_risk_score"],
                    analysis_data["executive_summary"]["confidence_level"],
                    15.7,  # Sample processing time
                )

                logger.info(
                    f"Created sample analysis for contract {contract['contract_type']}"
                )

        finally:
            await conn.close()

    async def seed_usage_logs(self, demo_users: List[Dict]):
        """Create sample usage logs for billing tracking"""
        logger.info("Seeding usage logs...")

        conn = await self.get_db_connection()
        try:
            # Create usage logs for the past month
            base_date = datetime.now() - timedelta(days=30)

            for user in demo_users:
                for i in range(5):  # 5 usage logs per user
                    log_date = base_date + timedelta(days=i * 6)

                    await conn.execute(
                        """
                        INSERT INTO usage_logs (user_id, action_type, credits_used, credits_remaining, metadata, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                        user["id"],
                        "contract_analysis",
                        1,
                        user["credits_remaining"]
                        + (5 - i),  # Simulate decreasing credits
                        json.dumps({"analysis_type": "standard", "file_size_mb": 2.1}),
                        log_date,
                    )

                logger.info(f"Created usage logs for {user['email']}")

        finally:
            await conn.close()

    async def seed_property_data(self, contracts: List[Dict]):
        """Create sample property data using the new properties table structure"""
        logger.info("Seeding property data...")

        sample_properties = [
            {
                "address_full": "15/45 George Street, Sydney NSW 2000",
                "street_number": "45",
                "street_name": "George Street",
                "suburb": "Sydney",
                "state": "NSW",
                "postcode": "2000",
                "property_type": "unit",
                "bedrooms": 2,
                "bathrooms": 2,
                "car_spaces": 1,
                "land_size": None,
                "building_size": 95.0,
                "latitude": -33.8688,
                "longitude": 151.2093,
                "year_built": 2010,
            },
            {
                "address_full": "123 Collins Street, Melbourne VIC 3000",
                "street_number": "123",
                "street_name": "Collins Street",
                "suburb": "Melbourne",
                "state": "VIC",
                "postcode": "3000",
                "property_type": "commercial",
                "bedrooms": None,
                "bathrooms": 2,
                "car_spaces": 0,
                "land_size": None,
                "building_size": 150.0,
                "latitude": -37.8136,
                "longitude": 144.9631,
                "year_built": 1985,
            },
        ]

        conn = await self.get_db_connection()
        try:
            property_ids = []
            for i, prop in enumerate(sample_properties[:2]):
                if i < len(contracts):
                    contract = contracts[i]

                    # Generate property_hash for shared property data
                    property_address = prop["address_full"]
                    property_hash = hashlib.sha256(
                        property_address.lower().encode()
                    ).hexdigest()

                    # Insert into properties table
                    property_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO properties (
                            id, property_hash, address_full, street_number, street_name, 
                            suburb, state, postcode, property_type, bedrooms, bathrooms, 
                            car_spaces, land_size, building_size, latitude, longitude, year_built,
                            address_verified, coordinates_verified, data_source
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                        ON CONFLICT (property_hash) DO NOTHING
                    """,
                        property_id,
                        property_hash,
                        prop["address_full"],
                        prop["street_number"],
                        prop["street_name"],
                        prop["suburb"],
                        prop["state"],
                        prop["postcode"],
                        prop["property_type"],
                        prop["bedrooms"],
                        prop["bathrooms"],
                        prop["car_spaces"],
                        prop["land_size"],
                        prop["building_size"],
                        prop["latitude"],
                        prop["longitude"],
                        prop["year_built"],
                        True,  # address_verified
                        True,  # coordinates_verified
                        "seed_data",  # data_source
                    )

                    # Create sample property valuation
                    valuation_id = str(uuid.uuid4())
                    valuation_value = 850000.00 if i == 0 else 650000.00
                    await conn.execute(
                        """
                        INSERT INTO property_valuations (
                            id, property_id, valuation_source, valuation_type, 
                            estimated_value, confidence, valuation_date
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT DO NOTHING
                    """,
                        valuation_id,
                        property_id,
                        "automated",
                        "market_estimate",
                        valuation_value,
                        0.85,
                        datetime.now(),
                    )

                    # Create sample market data
                    market_data_id = str(uuid.uuid4())
                    median_price = 820000 if i == 0 else 580000
                    await conn.execute(
                        """
                        INSERT INTO property_market_data (
                            id, property_id, suburb, state, data_source,
                            median_price, price_growth_12_month, rental_yield, 
                            days_on_market, data_date
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT DO NOTHING
                    """,
                        market_data_id,
                        property_id,
                        prop["suburb"],
                        prop["state"],
                        "market_api",
                        median_price,
                        8.2,  # 8.2% growth
                        4.5,  # 4.5% yield
                        32,   # days on market
                        datetime.now(),
                    )

                    # Create user_property_views entry for user access
                    await conn.execute(
                        """
                        INSERT INTO user_property_views (user_id, property_hash, property_address, source)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        contract["user_id"],
                        property_hash,
                        property_address,
                        "search",
                    )

                    property_ids.append({
                        "id": property_id,
                        "property_hash": property_hash,
                        "address": property_address
                    })

                    logger.info(f"Created property data for {prop['address_full']}")

            return property_ids

        finally:
            await conn.close()

    async def seed_analysis_progress(self, contracts: List[Dict]):
        """Create sample analysis progress records"""
        logger.info("Seeding analysis progress...")

        conn = await self.get_db_connection()
        try:
            for contract in contracts[:2]:  # Create progress for first 2 contracts
                progress_id = str(uuid.uuid4())
                
                # Create a progress record showing completed analysis
                await conn.execute(
                    """
                    INSERT INTO analysis_progress (
                        id, content_hash, user_id, current_step, progress_percent,
                        step_description, status, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (content_hash, user_id) DO UPDATE SET
                        current_step = EXCLUDED.current_step,
                        progress_percent = EXCLUDED.progress_percent,
                        step_description = EXCLUDED.step_description,
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata
                    """,
                    progress_id,
                    contract["content_hash"],
                    contract["user_id"],
                    "completed",
                    100,
                    "Contract analysis completed successfully",
                    "completed",
                    json.dumps({
                        "contract_type": contract.get("contract_type", "unknown"),
                        "analysis_type": "full_analysis",
                        "processing_time": 15.7
                    })
                )

                logger.info(f"Created analysis progress for contract {contract['content_hash'][:8]}...")

        finally:
            await conn.close()

    async def seed_artifact_data(self, documents: List[Dict]):
        """Create sample artifact data for content-addressed caching system"""
        logger.info("Seeding artifact data...")

        conn = await self.get_db_connection()
        try:
            for i, doc in enumerate(documents[:2]):  # Create artifacts for first 2 documents
                # Generate content HMAC for artifact system (simplified for demo)
                content_hmac = hashlib.sha256(f"document_content_{i}".encode()).hexdigest()
                algorithm_version = 1
                params_fingerprint = hashlib.sha256("default_params".encode()).hexdigest()

                # Create text extraction artifact
                artifact_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO text_extraction_artifacts (
                        id, content_hmac, algorithm_version, params_fingerprint,
                        full_text_uri, full_text_sha256, total_pages, total_words, methods
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (content_hmac, algorithm_version, params_fingerprint) DO NOTHING
                    """,
                    artifact_id,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                    f"s3://artifacts/text/{content_hmac}.txt",
                    hashlib.sha256(f"full_text_{i}".encode()).hexdigest(),
                    5 + i,  # page count
                    1200 + (i * 300),  # word count
                    json.dumps({
                        "extraction_method": "mupdf_primary",
                        "ocr_fallback": False,
                        "confidence": 0.95
                    })
                )

                # Update document with artifact reference
                await conn.execute(
                    """
                    UPDATE documents 
                    SET artifact_text_id = (
                        SELECT id FROM text_extraction_artifacts 
                        WHERE content_hmac = $2 
                        AND algorithm_version = $3 
                        AND params_fingerprint = $4
                    )
                    WHERE id = $1
                    """,
                    doc["id"],
                    content_hmac,
                    algorithm_version,
                    params_fingerprint
                )

                # Create sample page artifacts
                for page_num in range(1, 4):  # 3 pages per document
                    page_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO artifact_pages (
                            id, content_hmac, algorithm_version, params_fingerprint,
                            page_number, page_text_uri, page_text_sha256, layout, metrics
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number) DO NOTHING
                        """,
                        page_id,
                        content_hmac,
                        algorithm_version,
                        params_fingerprint,
                        page_num,
                        f"s3://artifacts/pages/{content_hmac}_p{page_num}.txt",
                        hashlib.sha256(f"page_text_{i}_{page_num}".encode()).hexdigest(),
                        json.dumps({
                            "bounding_box": {"x": 0, "y": 0, "width": 595, "height": 842},
                            "text_regions": 3,
                            "confidence": 0.92
                        }),
                        json.dumps({
                            "word_count": 180 + (page_num * 20),
                            "line_count": 25 + page_num,
                            "extraction_time_ms": 150 + (page_num * 10)
                        })
                    )

                # Create sample paragraph artifacts
                for page_num in range(1, 4):
                    for para_idx in range(3):  # 3 paragraphs per page
                        para_id = str(uuid.uuid4())
                        await conn.execute(
                            """
                            INSERT INTO artifact_paragraphs (
                                id, content_hmac, algorithm_version, params_fingerprint,
                                page_number, paragraph_index, paragraph_text_uri, paragraph_text_sha256, features
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number, paragraph_index) DO NOTHING
                            """,
                            para_id,
                            content_hmac,
                            algorithm_version,
                            params_fingerprint,
                            page_num,
                            para_idx,
                            f"s3://artifacts/paragraphs/{content_hmac}_p{page_num}_para{para_idx}.txt",
                            hashlib.sha256(f"paragraph_text_{i}_{page_num}_{para_idx}".encode()).hexdigest(),
                            json.dumps({
                                "clause_type": "general" if para_idx == 0 else "specific",
                                "importance": "high" if para_idx == 1 else "medium",
                                "risk_indicators": []  
                            })
                        )

                # Create user document associations
                for page_num in range(1, 4):
                    await conn.execute(
                        """
                        INSERT INTO user_document_pages (
                            document_id, page_number, artifact_page_id
                        ) 
                        SELECT $1, $2, id FROM artifact_pages 
                        WHERE content_hmac = $3 AND page_number = $2
                        ON CONFLICT DO NOTHING
                        """,
                        doc["id"],
                        page_num,
                        content_hmac
                    )

                    # Create paragraph associations
                    for para_idx in range(3):
                        await conn.execute(
                            """
                            INSERT INTO user_document_paragraphs (
                                document_id, page_number, paragraph_index, artifact_paragraph_id
                            )
                            SELECT $1, $2, $3, id FROM artifact_paragraphs 
                            WHERE content_hmac = $4 AND page_number = $2 AND paragraph_index = $3
                            ON CONFLICT DO NOTHING
                            """,
                            doc["id"],
                            page_num,
                            para_idx,
                            content_hmac
                        )

                logger.info(f"Created artifact data for document {doc['original_filename']}")

        finally:
            await conn.close()

    async def seed_processing_runs(self, documents: List[Dict]):
        """Create sample document processing runs and steps"""
        logger.info("Seeding processing runs...")

        conn = await self.get_db_connection()
        try:
            for doc in documents[:2]:  # Create processing runs for first 2 documents
                run_id = str(uuid.uuid4())
                
                # Create processing run
                await conn.execute(
                    """
                    INSERT INTO document_processing_runs (
                        run_id, document_id, user_id, status, last_step
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT DO NOTHING
                    """,
                    run_id,
                    doc["id"],
                    doc["user_id"],
                    "completed",
                    "analysis_complete"
                )

                # Create processing steps
                steps = [
                    ("extract_text", "success"),
                    ("parse_content", "success"),
                    ("analyze_contract", "success"),
                    ("generate_report", "success")
                ]

                for step_name, status in steps:
                    await conn.execute(
                        """
                        INSERT INTO document_processing_steps (
                            run_id, step_name, status, state_snapshot, completed_at
                        ) VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT DO NOTHING
                        """,
                        run_id,
                        step_name,
                        status,
                        json.dumps({
                            "step": step_name,
                            "processing_time_ms": 1500 + (hash(step_name) % 500)
                        }),
                        datetime.now()
                    )

                logger.info(f"Created processing run for document {doc['original_filename']}")

        finally:
            await conn.close()

    async def seed_user_views(self, contracts: List[Dict], properties: List[Dict] = None):
        """Create sample user tracking views"""
        logger.info("Seeding user tracking views...")

        conn = await self.get_db_connection()
        try:
            # Create contract views
            for contract in contracts:
                view_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO user_contract_views (
                        id, user_id, content_hash, property_address, source
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT DO NOTHING
                    """,
                    view_id,
                    contract["user_id"],
                    contract["content_hash"],
                    None,  # property_address - could be populated from property data
                    "upload"
                )

            # Create property views if properties provided
            if properties:
                for prop in properties:
                    view_id = str(uuid.uuid4())
                    # Find a user_id from contracts for this property view
                    user_id = contracts[0]["user_id"] if contracts else None
                    if user_id:
                        await conn.execute(
                            """
                            INSERT INTO user_property_views (
                                id, user_id, property_hash, property_address, source
                            ) VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT DO NOTHING
                            """,
                            view_id,
                            user_id,
                            prop["property_hash"],
                            prop["address"],
                            "search"
                        )

            logger.info("Created user tracking views")

        finally:
            await conn.close()

    async def seed_all(
        self,
        include_documents=False,
        include_contracts=False,
        include_analyses=False,
        include_usage_logs=False,
        include_property_data=False,
        include_artifacts=False,
        include_processing_runs=False,
        include_user_views=False,
    ):
        """Seed sample data based on provided options"""
        logger.info("🌱 Starting database seeding...")

        try:
            # Always seed demo users/profiles
            demo_users = await self.seed_demo_users()
            logger.info(f"✅ Created {len(demo_users)} demo user profiles")

            # Seed additional data only if requested
            documents = []
            contracts = []

            if include_documents:
                documents = await self.seed_sample_documents(demo_users)
                logger.info(f"✅ Created {len(documents)} sample documents")

                # Create artifact data if requested
                if include_artifacts:
                    await self.seed_artifact_data(documents)
                    logger.info("✅ Created sample artifact data")

            if include_contracts and documents:
                contracts = await self.seed_sample_contracts(documents)
                logger.info(f"✅ Created {len(contracts)} sample contracts")

            if include_analyses and contracts:
                await self.seed_sample_analyses(contracts)
                logger.info("✅ Created sample analyses")
                
                # Also create analysis progress records
                await self.seed_analysis_progress(contracts)
                logger.info("✅ Created analysis progress records")

            if include_usage_logs:
                await self.seed_usage_logs(demo_users)
                logger.info("✅ Created usage logs")

            properties = []
            if include_property_data and contracts:
                properties = await self.seed_property_data(contracts)
                logger.info(f"✅ Created {len(properties)} properties with market data")

            if include_processing_runs and documents:
                await self.seed_processing_runs(documents)
                logger.info("✅ Created sample processing runs")

            if include_user_views and (contracts or properties):
                await self.seed_user_views(contracts, properties)
                logger.info("✅ Created sample user tracking views")

            logger.info("✅ Database seeding completed successfully!")

        except Exception as e:
            logger.error(f"❌ Database seeding failed: {e}")
            raise


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Seed the Real2.AI database with sample data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_database.py                    # Only create sample profiles
  python seed_database.py --all              # Create all sample data
  python seed_database.py --documents --contracts  # Create profiles, documents, and contracts
  python seed_database.py --reset --all      # Reset and create all sample data
        """,
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing data before seeding (requires confirmation)",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Create all sample data (profiles, documents, contracts, analyses, artifacts, usage logs, property data, processing runs, user views)",
    )

    parser.add_argument(
        "--documents", action="store_true", help="Create sample documents"
    )

    parser.add_argument(
        "--contracts",
        action="store_true",
        help="Create sample contracts (requires --documents)",
    )

    parser.add_argument(
        "--analyses",
        action="store_true",
        help="Create sample analyses (requires --contracts)",
    )

    parser.add_argument(
        "--usage-logs", action="store_true", help="Create sample usage logs"
    )

    parser.add_argument(
        "--property-data",
        action="store_true", 
        help="Create sample property data (requires --contracts)",
    )

    parser.add_argument(
        "--artifacts",
        action="store_true",
        help="Create sample artifact data (requires --documents)",
    )

    parser.add_argument(
        "--processing-runs",
        action="store_true",
        help="Create sample processing runs (requires --documents)",
    )

    parser.add_argument(
        "--user-views",
        action="store_true",
        help="Create sample user tracking views (requires --contracts or --property-data)",
    )

    return parser.parse_args()


async def main():
    args = parse_arguments()

    if args.reset:
        logger.warning("🚨 This will delete all existing data and reseed!")
        confirmation = input("Type 'SEED' to confirm: ")
        if confirmation != "SEED":
            logger.info("Seeding cancelled")
            return

    try:
        seeder = DatabaseSeeder()
        await seeder.initialize()

        # Determine what to seed based on arguments
        if args.all:
            # Create all sample data
            await seeder.seed_all(
                include_documents=True,
                include_contracts=True,
                include_analyses=True,
                include_artifacts=True,
                include_usage_logs=True,
                include_property_data=True,
                include_processing_runs=True,
                include_user_views=True,
            )
        else:
            # Only create profiles by default, plus any additional data requested
            await seeder.seed_all(
                include_documents=args.documents,
                include_contracts=args.contracts,
                include_analyses=args.analyses,
                include_artifacts=args.artifacts,
                include_usage_logs=args.usage_logs,
                include_property_data=args.property_data,
                include_processing_runs=getattr(args, 'processing_runs', False),
                include_user_views=getattr(args, 'user_views', False),
            )

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

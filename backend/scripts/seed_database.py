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
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_database_client, init_database

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

        # Use the same database client as the main app
        self.db_client = get_database_client()

    async def initialize(self):
        """Initialize the database connection"""
        await init_database()

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
                "password": "demo123456",
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
                        logger.info(f"Attempting to create auth user for {user['email']}")
                        
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
                            logger.info(f"Created auth user: {user['email']} with ID: {auth_user_id}")
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
                            logger.info(f"Profile already exists for: {user['email']}")
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
                        logger.error(f"Failed to create profile for {user['email']}: {e}")

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
                available_users.append(available_users[-1] if available_users else demo_users[0])

        sample_documents = [
            {
                "user_id": available_users[0]["id"],  # demo user
                "filename": "Demo_Contract_Analysis.pdf",
                "storage_path": f"{available_users[0]['id']}/2024/01/15/demo_contract_001.pdf",
                "file_type": "application/pdf",
                "file_size": 2048576,  # 2MB
                "status": "processed",
            },
            {
                "user_id": available_users[0]["id"],  # demo user
                "filename": "Demo_Property_Contract.pdf",
                "storage_path": f"{available_users[0]['id']}/2024/01/20/demo_contract_002.pdf",
                "file_type": "application/pdf",
                "file_size": 3145728,  # 3MB
                "status": "processed",
            },
            {
                "user_id": available_users[1]["id"],  # investor
                "filename": "Purchase_Agreement_Sydney_Unit.pdf",
                "storage_path": f"{available_users[1]['id']}/2024/01/15/contract_001.pdf",
                "file_type": "application/pdf",
                "file_size": 2048576,  # 2MB
                "status": "processed",
            },
            {
                "user_id": available_users[1]["id"],  # investor
                "filename": "Off_Plan_Contract_Parramatta.pdf",
                "storage_path": f"{available_users[1]['id']}/2024/01/20/contract_002.pdf",
                "file_type": "application/pdf",
                "file_size": 3145728,  # 3MB
                "status": "processed",
            },
            {
                "user_id": available_users[2]["id"],  # agent
                "filename": "Lease_Agreement_Melbourne_CBD.pdf",
                "storage_path": f"{available_users[2]['id']}/2024/01/18/lease_001.pdf",
                "file_type": "application/pdf",
                "file_size": 1572864,  # 1.5MB
                "status": "processed",
            },
            {
                "user_id": available_users[3]["id"],  # buyer
                "filename": "House_Purchase_Brisbane.pdf",
                "storage_path": f"{available_users[3]['id']}/2024/01/25/house_001.pdf",
                "file_type": "application/pdf",
                "file_size": 2621440,  # 2.5MB
                "status": "processed",
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
                        INSERT INTO documents (id, user_id, filename, storage_path, file_type, file_size, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (id) DO NOTHING
                    """,
                        doc_id,
                        doc["user_id"],
                        doc["filename"],
                        doc["storage_path"],
                        doc["file_type"],
                        doc["file_size"],
                        doc["status"],
                    )

                    document_ids.append({**doc, "id": doc_id})
                    logger.info(f"Created sample document: {doc['filename']}")
                except Exception as e:
                    logger.error(f"Failed to create document {doc['filename']}: {e}")

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
                    "sydney" in doc["filename"].lower()
                    or "parramatta" in doc["filename"].lower()
                ):
                    state = "NSW"
                elif "melbourne" in doc["filename"].lower():
                    state = "VIC"
                elif "brisbane" in doc["filename"].lower():
                    state = "QLD"
                else:
                    state = "NSW"  # default

                await conn.execute(
                    """
                    INSERT INTO contracts (id, document_id, user_id, contract_type, australian_state)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO NOTHING
                """,
                    contract_id,
                    doc["id"],
                    doc["user_id"],
                    contract_type,
                    state,
                )

                contract_ids.append(
                    {
                        "id": contract_id,
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
                        id, contract_id, user_id, agent_version, status, 
                        executive_summary, risk_assessment, compliance_check, recommendations,
                        overall_risk_score, confidence_level, processing_time_seconds
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (id) DO NOTHING
                """,
                    analysis_id,
                    contract["id"],
                    contract["user_id"],
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
        """Create sample property data"""
        logger.info("Seeding property data...")

        sample_properties = [
            {
                "address": "15/45 George Street, Sydney NSW 2000",
                "suburb": "Sydney",
                "state": "NSW",
                "postcode": "2000",
                "property_type": "unit",
                "bedrooms": 2,
                "bathrooms": 2,
                "car_spaces": 1,
                "land_size": None,
                "building_size": 95.0,
                "purchase_price": 850000.00,
                "market_value": 875000.00,
            },
            {
                "address": "123 Collins Street, Melbourne VIC 3000",
                "suburb": "Melbourne",
                "state": "VIC",
                "postcode": "3000",
                "property_type": "commercial",
                "bedrooms": None,
                "bathrooms": 2,
                "car_spaces": 0,
                "land_size": None,
                "building_size": 150.0,
                "purchase_price": None,  # Lease
                "market_value": 650000.00,
            },
        ]

        conn = await self.get_db_connection()
        try:
            for i, prop in enumerate(sample_properties[:2]):
                if i < len(contracts):
                    contract = contracts[i]

                    await conn.execute(
                        """
                        INSERT INTO property_data (
                            contract_id, user_id, address, suburb, state, postcode,
                            property_type, bedrooms, bathrooms, car_spaces,
                            land_size, building_size, purchase_price, market_value,
                            market_analysis
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        ON CONFLICT DO NOTHING
                    """,
                        contract["id"],
                        contract["user_id"],
                        prop["address"],
                        prop["suburb"],
                        prop["state"],
                        prop["postcode"],
                        prop["property_type"],
                        prop["bedrooms"],
                        prop["bathrooms"],
                        prop["car_spaces"],
                        prop["land_size"],
                        prop["building_size"],
                        prop["purchase_price"],
                        prop["market_value"],
                        json.dumps(
                            {
                                "median_price_suburb": 820000,
                                "price_growth_12m": 0.08,
                                "rental_yield": 0.045,
                                "days_on_market": 32,
                            }
                        ),
                    )

                    logger.info(f"Created property data for {prop['address']}")

        finally:
            await conn.close()

    async def seed_all(self):
        """Seed all sample data"""
        logger.info("🌱 Starting database seeding...")

        try:
            # Seed in dependency order
            demo_users = await self.seed_demo_users()
            documents = await self.seed_sample_documents(demo_users)
            contracts = await self.seed_sample_contracts(documents)
            await self.seed_sample_analyses(contracts)
            await self.seed_usage_logs(demo_users)
            await self.seed_property_data(contracts)

            logger.info("✅ Database seeding completed successfully!")

        except Exception as e:
            logger.error(f"❌ Database seeding failed: {e}")
            raise


async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        logger.warning("🚨 This will delete all existing data and reseed!")
        confirmation = input("Type 'SEED' to confirm: ")
        if confirmation != "SEED":
            logger.info("Seeding cancelled")
            return

    try:
        seeder = DatabaseSeeder()
        await seeder.initialize()
        await seeder.seed_all()
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

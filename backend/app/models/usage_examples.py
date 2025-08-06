"""
Usage Examples for Supabase Models with Automatic Timestamps
Demonstrates how to use the models without manually managing timestamps
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Dict, Any, List

from supabase import create_client, Client
from app.models.supabase_models import (
    Profile, Document, Contract, ContractAnalysis,
    DocumentPage, DocumentEntity, DocumentDiagram,
    SupabaseModelManager, AustralianState, UserType,
    DocumentStatus, ContractType, AnalysisStatus
)

# Initialize Supabase client
def get_supabase_client(url: str, key: str) -> Client:
    """Initialize Supabase client"""
    return create_client(url, key)

# Example usage with automatic timestamp management
class TimestampExamples:
    """Examples of using models with automatic timestamps"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.manager = SupabaseModelManager(supabase_client)
    
    async def create_user_profile_example(self) -> Dict[str, Any]:
        """Example: Creating a user profile - timestamps handled automatically"""
        
        # Create profile data - NO need to set created_at or updated_at
        profile_data = {
            "id": uuid4(),
            "email": "user@example.com",
            "full_name": "John Smith",
            "phone_number": "+61412345678",
            "australian_state": AustralianState.NSW,
            "user_type": UserType.BUYER,
            "credits_remaining": 5,
            "preferences": {"notifications": True, "theme": "dark"},
            "onboarding_completed": False
        }
        
        # Create record using the model manager
        created_profile = await self.manager.create_record(
            "profiles", Profile, **profile_data
        )
        
        print(f"✅ Profile created with automatic timestamps:")
        print(f"   ID: {created_profile['id']}")
        print(f"   Created at: {created_profile['created_at']}")  # Set by database DEFAULT NOW()
        print(f"   Updated at: {created_profile['updated_at']}")  # Set by database DEFAULT NOW()
        
        return created_profile
    
    async def update_user_profile_example(self, profile_id: str) -> Dict[str, Any]:
        """Example: Updating a user profile - updated_at handled automatically"""
        
        # Update profile data - NO need to set updated_at
        update_data = {
            "full_name": "John Michael Smith",
            "onboarding_completed": True,
            "onboarding_completed_at": datetime.utcnow(),
            "onboarding_preferences": {
                "practice_area": "property",
                "jurisdiction": "nsw",
                "firm_size": "solo"
            }
        }
        
        # Update record using the model manager
        updated_profile = await self.manager.update_record(
            "profiles", profile_id, Profile, **update_data
        )
        
        print(f"✅ Profile updated with automatic timestamp:")
        print(f"   ID: {updated_profile['id']}")
        print(f"   Created at: {updated_profile['created_at']}")  # Unchanged
        print(f"   Updated at: {updated_profile['updated_at']}")  # Automatically updated by trigger
        
        return updated_profile
    
    async def create_document_example(self, user_id: UUID) -> Dict[str, Any]:
        """Example: Creating a document - timestamps managed automatically"""
        
        document_data = {
            "id": uuid4(),
            "user_id": user_id,
            "original_filename": "contract.pdf",
            "storage_path": "documents/2024/01/contract.pdf",
            "file_type": "application/pdf",
            "file_size": 2048000,
            "processing_status": DocumentStatus.UPLOADED.value,
            "upload_metadata": {"client_ip": "192.168.1.1", "user_agent": "Mozilla/5.0"},
            "total_pages": 25,
            "document_type": "purchase_agreement",
            "australian_state": "NSW",
            "contract_type": "purchase_agreement"
        }
        
        created_document = await self.manager.create_record(
            "documents", Document, **document_data
        )
        
        print(f"✅ Document created with automatic timestamps:")
        print(f"   ID: {created_document['id']}")
        print(f"   Filename: {created_document['original_filename']}")
        print(f"   Created at: {created_document['created_at']}")
        print(f"   Updated at: {created_document['updated_at']}")
        
        return created_document
    
    async def update_document_processing_example(self, document_id: str) -> Dict[str, Any]:
        """Example: Updating document processing status - updated_at handled automatically"""
        
        # Update processing status and metrics
        update_data = {
            "processing_status": DocumentStatus.PROCESSING.value,
            "processing_started_at": datetime.utcnow(),
            "overall_quality_score": 0.85,
            "extraction_confidence": 0.92,
            "text_extraction_method": "gemini_ocr",
            "total_text_length": 45000,
            "total_word_count": 7500,
            "has_diagrams": True,
            "diagram_count": 3
        }
        
        updated_document = await self.manager.update_record(
            "documents", document_id, Document, **update_data
        )
        
        print(f"✅ Document processing updated:")
        print(f"   Status: {updated_document['processing_status']}")
        print(f"   Quality Score: {updated_document['overall_quality_score']}")
        print(f"   Updated at: {updated_document['updated_at']}")  # Automatically updated
        
        return updated_document
    
    async def create_contract_analysis_example(
        self, contract_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """Example: Creating contract analysis - timestamps managed automatically"""
        
        analysis_data = {
            "id": uuid4(),
            "contract_id": contract_id,
            "user_id": user_id,
            "agent_version": "2.0",
            "status": AnalysisStatus.PROCESSING.value,
            "analysis_result": {},
            "executive_summary": {
                "overall_risk_score": 0.0,
                "confidence_level": 0.0,
                "key_findings": []
            },
            "risk_assessment": {},
            "compliance_check": {},
            "recommendations": [],
            "analysis_metadata": {
                "model_version": "gpt-4",
                "processing_priority": "standard"
            }
        }
        
        created_analysis = await self.manager.create_record(
            "contract_analyses", ContractAnalysis, **analysis_data
        )
        
        print(f"✅ Contract analysis created:")
        print(f"   ID: {created_analysis['id']}")
        print(f"   Status: {created_analysis['status']}")
        print(f"   Created at: {created_analysis['created_at']}")
        
        return created_analysis
    
    async def complete_contract_analysis_example(
        self, analysis_id: str
    ) -> Dict[str, Any]:
        """Example: Completing contract analysis - updated_at handled automatically"""
        
        completion_data = {
            "status": AnalysisStatus.COMPLETED.value,
            "analysis_result": {
                "contract_terms_extracted": 47,
                "risk_factors_identified": 8,
                "compliance_issues": 2
            },
            "executive_summary": {
                "overall_risk_score": 6.5,
                "confidence_level": 0.89,
                "key_findings": [
                    "Settlement period is 42 days",
                    "No cooling-off period waiver",
                    "Property sold as-is"
                ]
            },
            "risk_assessment": {
                "high_risk_factors": 2,
                "medium_risk_factors": 4,
                "low_risk_factors": 2
            },
            "compliance_check": {
                "nsw_compliance": True,
                "disclosure_requirements_met": True,
                "cooling_off_compliant": True
            },
            "recommendations": [
                {
                    "priority": "high",
                    "category": "legal",
                    "recommendation": "Consider building and pest inspection",
                    "action_required": True
                }
            ],
            "overall_risk_score": 6.5,
            "confidence_level": 0.89,
            "processing_time_seconds": 127.5,
            "analysis_timestamp": datetime.utcnow()
        }
        
        completed_analysis = await self.manager.update_record(
            "contract_analyses", analysis_id, ContractAnalysis, **completion_data
        )
        
        print(f"✅ Contract analysis completed:")
        print(f"   Risk Score: {completed_analysis['overall_risk_score']}")
        print(f"   Confidence: {completed_analysis['confidence_level']}")
        print(f"   Processing Time: {completed_analysis['processing_time_seconds']}s")
        print(f"   Updated at: {completed_analysis['updated_at']}")  # Auto-updated by trigger
        
        return completed_analysis
    
    async def create_document_page_example(
        self, document_id: UUID, page_number: int
    ) -> Dict[str, Any]:
        """Example: Creating document page - timestamps handled automatically"""
        
        page_data = {
            "id": uuid4(),
            "document_id": document_id,
            "page_number": page_number,
            "content_summary": "Page contains property details and financial terms",
            "text_content": "PROPERTY PURCHASE AGREEMENT...",
            "text_length": 2450,
            "word_count": 420,
            "content_types": ["text", "table"],
            "primary_content_type": "text",
            "extraction_confidence": 0.94,
            "content_quality_score": 0.88,
            "has_header": True,
            "has_footer": True,
            "has_signatures": False,
            "has_handwriting": False,
            "has_diagrams": False,
            "has_tables": True,
            "processed_at": datetime.utcnow(),
            "processing_method": "gemini_2.5_pro"
        }
        
        created_page = await self.manager.create_record(
            "document_pages", DocumentPage, **page_data
        )
        
        print(f"✅ Document page created:")
        print(f"   Page: {created_page['page_number']}")
        print(f"   Words: {created_page['word_count']}")
        print(f"   Created at: {created_page['created_at']}")
        
        return created_page
    
    async def batch_create_entities_example(
        self, document_id: UUID, entities_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Example: Batch creating entities - all timestamps handled automatically"""
        
        created_entities = []
        
        for entity_data in entities_data:
            entity_record = {
                "id": uuid4(),
                "document_id": document_id,
                "page_number": entity_data["page_number"],
                "entity_type": entity_data["entity_type"],
                "entity_value": entity_data["entity_value"],
                "normalized_value": entity_data.get("normalized_value"),
                "context": entity_data.get("context"),
                "confidence": entity_data.get("confidence", 0.0),
                "extraction_method": "gemini_2.5_pro",
                "position_data": entity_data.get("position_data"),
                "extracted_at": datetime.utcnow()
            }
            
            created_entity = await self.manager.create_record(
                "document_entities", DocumentEntity, **entity_record
            )
            created_entities.append(created_entity)
        
        print(f"✅ Created {len(created_entities)} entities with automatic timestamps")
        return created_entities
    
    async def query_recent_records_example(self) -> Dict[str, List[Dict[str, Any]]]:
        """Example: Querying recent records using timestamp indexes"""
        
        # Get recent documents (last 24 hours)
        recent_documents = await self.manager.list_records(
            "documents"
        )
        
        # Filter by created_at in application (or use SQL functions)
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        recent_docs = [
            doc for doc in recent_documents 
            if doc.get('created_at') and 
            datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00')) > yesterday
        ]
        
        print(f"✅ Found {len(recent_docs)} documents created in last 24 hours")
        
        # Get recently updated profiles
        recent_profiles = self.client.table("profiles") \
            .select("*") \
            .gte("updated_at", yesterday.isoformat()) \
            .order("updated_at.desc") \
            .execute()
        
        print(f"✅ Found {len(recent_profiles.data)} profiles updated recently")
        
        return {
            "recent_documents": recent_docs,
            "recent_profiles": recent_profiles.data
        }

    async def demonstrate_timestamp_preservation_example(self, profile_id: str):
        """Example: Demonstrating that created_at is preserved during updates"""
        
        # Get original record
        original = await self.manager.get_record("profiles", profile_id)
        original_created_at = original['created_at']
        
        print(f"🔍 Original created_at: {original_created_at}")
        
        # Update the record
        updated = await self.manager.update_record(
            "profiles", profile_id, Profile,
            full_name="Updated Name",
            preferences={"theme": "light"}
        )
        
        print(f"🔍 After update:")
        print(f"   Created at: {updated['created_at']} (should be unchanged)")
        print(f"   Updated at: {updated['updated_at']} (should be different)")
        print(f"   ✅ Created timestamp preserved: {updated['created_at'] == original_created_at}")


# Usage in FastAPI endpoints
class TimestampAPIExamples:
    """Examples for FastAPI endpoints using automatic timestamps"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.manager = SupabaseModelManager(supabase_client)
    
    async def create_document_endpoint(
        self, 
        user_id: str,
        filename: str, 
        file_size: int,
        file_type: str
    ) -> Dict[str, Any]:
        """FastAPI endpoint example for document creation"""
        
        try:
            # Create document record - timestamps handled automatically
            document_data = {
                "id": uuid4(),
                "user_id": UUID(user_id),
                "original_filename": filename,
                "storage_path": f"documents/{datetime.utcnow().year}/{filename}",
                "file_type": file_type,
                "file_size": file_size,
                "processing_status": DocumentStatus.UPLOADED.value
            }
            
            document = await self.manager.create_record(
                "documents", Document, **document_data
            )
            
            return {
                "success": True,
                "document_id": str(document["id"]),
                "created_at": document["created_at"],
                "message": "Document uploaded successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create document"
            }
    
    async def update_processing_status_endpoint(
        self, 
        document_id: str, 
        status: str,
        processing_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """FastAPI endpoint example for updating processing status"""
        
        try:
            update_data = {
                "processing_status": status,
                "processing_results": processing_results or {}
            }
            
            if status == DocumentStatus.PROCESSING.value:
                update_data["processing_started_at"] = datetime.utcnow()
            elif status in [DocumentStatus.ANALYSIS_COMPLETE.value, DocumentStatus.FAILED.value]:
                update_data["processing_completed_at"] = datetime.utcnow()
            
            # Update with automatic updated_at timestamp
            updated_document = await self.manager.update_record(
                "documents", document_id, Document, **update_data
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "status": updated_document["processing_status"],
                "updated_at": updated_document["updated_at"],
                "message": f"Document status updated to {status}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update document status"
            }


# Direct SQL examples (for advanced usage)
async def direct_sql_examples(supabase_client: Client):
    """Examples of using direct SQL with automatic timestamps"""
    
    # Example: Bulk insert with automatic timestamps
    bulk_insert_sql = """
    INSERT INTO document_entities (id, document_id, page_number, entity_type, entity_value, confidence)
    VALUES 
        (gen_random_uuid(), %s, 1, 'address', '123 Main St, Sydney NSW 2000', 0.95),
        (gen_random_uuid(), %s, 1, 'date', '2024-03-15', 0.88),
        (gen_random_uuid(), %s, 2, 'financial_amount', '$850,000', 0.92)
    RETURNING id, created_at, updated_at;
    """
    
    # Example: Update with timestamp verification
    update_with_verification_sql = """
    UPDATE documents 
    SET 
        processing_status = 'analysis_complete',
        overall_quality_score = 0.89
    WHERE id = %s
    RETURNING id, processing_status, created_at, updated_at;
    """
    
    # Example: Query recent records using timestamp indexes
    recent_records_sql = """
    SELECT id, original_filename, processing_status, created_at, updated_at
    FROM documents 
    WHERE created_at > NOW() - INTERVAL '24 hours'
    ORDER BY created_at DESC
    LIMIT 50;
    """
    
    # Example: Check timestamp consistency
    timestamp_consistency_sql = """
    SELECT 
        table_name,
        COUNT(*) as total_records,
        COUNT(created_at) as has_created_at,
        COUNT(updated_at) as has_updated_at,
        COUNT(*) - COUNT(created_at) as missing_created_at,
        COUNT(*) - COUNT(updated_at) as missing_updated_at
    FROM (
        SELECT 'profiles' as table_name, created_at, updated_at FROM profiles
        UNION ALL
        SELECT 'documents' as table_name, created_at, updated_at FROM documents
        UNION ALL
        SELECT 'contracts' as table_name, created_at, updated_at FROM contracts
    ) combined
    GROUP BY table_name;
    """
    
    print("📊 SQL examples for timestamp management:")
    print("1. Bulk insert:", bulk_insert_sql)
    print("2. Update with verification:", update_with_verification_sql)
    print("3. Recent records query:", recent_records_sql)
    print("4. Timestamp consistency check:", timestamp_consistency_sql)


if __name__ == "__main__":
    # Example usage
    import asyncio
    import os
    
    async def main():
        # Initialize Supabase client (replace with your credentials)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("⚠️  Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
            return
        
        client = get_supabase_client(supabase_url, supabase_key)
        examples = TimestampExamples(client)
        
        print("🚀 Running timestamp management examples...")
        
        # Create a user profile
        profile = await examples.create_user_profile_example()
        profile_id = str(profile['id'])
        
        # Update the profile
        await examples.update_user_profile_example(profile_id)
        
        # Create a document
        document = await examples.create_document_example(UUID(profile_id))
        document_id = str(document['id'])
        
        # Update document processing
        await examples.update_document_processing_example(document_id)
        
        # Query recent records
        await examples.query_recent_records_example()
        
        # Demonstrate timestamp preservation
        await examples.demonstrate_timestamp_preservation_example(profile_id)
        
        print("✅ All examples completed successfully!")
    
    # Run the examples
    # asyncio.run(main())
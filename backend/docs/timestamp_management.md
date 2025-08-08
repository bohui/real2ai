# Automatic Timestamp Management System

## Overview

This document describes the automatic timestamp management system implemented in the Real2.AI Supabase database. The system ensures that `created_at` and `updated_at` timestamps are handled automatically by the database, eliminating the need for manual timestamp management in application code.

## Architecture

### Database-Level Implementation

The timestamp management is implemented using:

1. **Default Values**: `created_at` columns use `DEFAULT NOW()` 
2. **Database Triggers**: `updated_at` columns are managed by `BEFORE UPDATE` triggers
3. **Trigger Function**: `update_updated_at_column()` handles timestamp updates
4. **Preservation Logic**: Ensures `created_at` is never modified after initial insert

### Key Components

#### 1. Trigger Function

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Set updated_at to current timestamp
    NEW.updated_at = NOW();
    
    -- Ensure created_at is never modified after initial insert
    IF TG_OP = 'UPDATE' AND OLD.created_at IS NOT NULL THEN
        NEW.created_at = OLD.created_at;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### 2. Automatic Triggers

Every table with timestamp columns has an automatic trigger:

```sql
CREATE TRIGGER update_{table_name}_updated_at 
    BEFORE UPDATE ON {table_name} 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Benefits

✅ **Zero Manual Management**: No need to set timestamps in application code  
✅ **Consistency Guaranteed**: All records have accurate timestamps  
✅ **Performance Optimized**: Database-level handling is faster  
✅ **Audit Trail**: Reliable tracking of record creation and modification  
✅ **Developer Friendly**: Reduces boilerplate code and prevents errors  

## Tables with Automatic Timestamps

| Table Name | created_at | updated_at | Trigger |
|------------|------------|------------|---------|
| profiles | ✅ | ✅ | ✅ |
| documents | ✅ | ✅ | ✅ |
| contracts | ✅ | ✅ | ✅ |
| contract_analyses | ✅ | ✅ | ✅ |
| document_pages | ✅ | ✅ | ✅ |
| document_entities | ✅ | ✅ | ✅ |
| document_diagrams | ✅ | ✅ | ✅ |
| document_analyses | ✅ | ✅ | ✅ |
| property_data | ✅ | ✅ | ✅ |
| user_subscriptions | ✅ | ✅ | ✅ |
| analysis_progress | ✅ | ✅ | ✅ |
| usage_logs | ✅* | ❌ | ❌ |
| subscription_plans | ✅ | ❌ | ❌ |

*Note: `usage_logs` uses `timestamp` field instead of `created_at`*

## Usage Guide

### 1. Creating Records

When creating records, **DO NOT** set `created_at` or `updated_at`:

```python
# ✅ CORRECT - Let database handle timestamps
document_data = {
    "id": uuid4(),
    "user_id": user_id,
    "original_filename": "contract.pdf",
    "file_type": "application/pdf",
    "file_size": 2048000,
    # created_at and updated_at automatically set by database
}

result = supabase.table("documents").insert(document_data).execute()
```

```python
# ❌ INCORRECT - Don't set timestamps manually
document_data = {
    "id": uuid4(),
    "user_id": user_id,
    "original_filename": "contract.pdf", 
    "created_at": datetime.utcnow(),  # ❌ Don't do this
    "updated_at": datetime.utcnow()   # ❌ Don't do this
}
```

### 2. Updating Records

When updating records, **DO NOT** set `updated_at`:

```python
# ✅ CORRECT - updated_at handled by trigger
update_data = {
    "processing_status": "completed",
    "overall_quality_score": 0.89
    # updated_at automatically set by trigger
}

result = (supabase.table("documents")
          .update(update_data)
          .eq("id", document_id)
          .execute())
```

```python
# ❌ INCORRECT - Don't set updated_at manually
update_data = {
    "processing_status": "completed",
    "updated_at": datetime.utcnow()  # ❌ Don't do this
}
```

### 3. Using Pydantic Models

The provided Pydantic models handle timestamps correctly:

```python
from app.models.supabase_models import SupabaseModelManager, Document

manager = SupabaseModelManager(supabase_client)

# Create record - timestamps excluded automatically
document = await manager.create_record("documents", Document, **data)

# Update record - timestamps excluded automatically  
updated_document = await manager.update_record("documents", doc_id, Document, **updates)
```

### 4. Model Helper Functions

Use the provided helper functions for clean data handling:

```python
from app.models.supabase_models import create_model_with_timestamps, update_model_with_timestamps

# For inserts - removes timestamp fields
insert_data = create_model_with_timestamps(Document, **raw_data)

# For updates - removes timestamp fields
update_data = update_model_with_timestamps(Document, **raw_updates)
```

## Database Management

### Monitoring Timestamp Configuration

Check timestamp configuration status:

```sql
SELECT * FROM timestamp_management_status;
```

Returns status for all tables:
- `OPTIMAL`: Perfect configuration (defaults + triggers)
- `GOOD`: Has triggers but may lack defaults
- `NEEDS_ATTENTION`: Missing triggers or defaults

### Verification Functions

#### Check Timestamp Defaults and Triggers

```sql
SELECT * FROM verify_timestamp_defaults();
```

#### Backfill Missing Timestamps (if needed)

```sql
SELECT backfill_timestamps('table_name');
```

### Performance Indexes

Automatic indexes are created for timestamp queries:

```sql
-- For querying recent records
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_updated_at ON documents(updated_at DESC);
```

## Advanced Usage

### Querying Recent Records

Use database functions for efficient timestamp queries:

```sql
-- Get records from last 24 hours
SELECT get_recent_records('documents', 24, 100);

-- Get recently updated records (last 60 minutes)  
SELECT get_recently_updated_records('profiles', 60, 50);
```

### Batch Operations

For bulk inserts, timestamps are still handled automatically:

```sql
INSERT INTO document_entities (id, document_id, entity_type, entity_value)
VALUES 
    (gen_random_uuid(), %s, 'address', '123 Main St'),
    (gen_random_uuid(), %s, 'date', '2024-03-15')
-- created_at and updated_at set automatically
RETURNING id, created_at, updated_at;
```

### FastAPI Integration

Example FastAPI endpoint with automatic timestamps:

```python
@app.post("/documents")
async def create_document(document_data: DocumentCreateRequest):
    """Create document with automatic timestamps"""
    
    # Model excludes timestamp fields automatically
    clean_data = create_model_with_timestamps(Document, **document_data.dict())
    
    result = supabase.table("documents").insert(clean_data).execute()
    
    return {
        "document_id": result.data[0]["id"],
        "created_at": result.data[0]["created_at"],  # Set by database
        "message": "Document created successfully"
    }
```

## Migration History

### Migration Files

1. **20240101000000_initial_schema.sql** - Initial schema with timestamp columns and enhanced timestamp management
2. **20240101000002_functions_triggers.sql** - Basic trigger setup and timestamp management functions

### Applying Migrations

Run migrations in order:

```bash
# Apply new timestamp management migration
supabase db push
```

## Best Practices

### ✅ DO

- Let the database handle all timestamp management
- Use the provided Pydantic models and helper functions
- Query using timestamp indexes for performance
- Monitor timestamp configuration with provided views
- Use `get_recent_records()` functions for efficient queries

### ❌ DON'T

- Set `created_at` or `updated_at` manually in application code
- Modify triggers or trigger functions without understanding impact
- Query timestamps without using indexes
- Assume timestamps will be in application timezone (they're UTC)

## Troubleshooting

### Common Issues

#### 1. Missing Timestamps

**Problem**: Records have `NULL` timestamps

**Solution**: Run backfill function
```sql
SELECT backfill_timestamps('table_name');
```

#### 2. Timestamps Not Updating

**Problem**: `updated_at` not changing on updates

**Check**: Verify trigger exists
```sql
SELECT * FROM pg_trigger WHERE tgname = 'update_table_name_updated_at';
```

**Fix**: Recreate trigger
```sql
CREATE TRIGGER update_table_name_updated_at 
    BEFORE UPDATE ON table_name 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

#### 3. Performance Issues

**Problem**: Slow timestamp queries

**Check**: Verify indexes exist
```sql
SELECT * FROM pg_indexes WHERE indexname LIKE '%created_at%' OR indexname LIKE '%updated_at%';
```

**Fix**: Create missing indexes
```sql
CREATE INDEX CONCURRENTLY idx_table_created_at ON table_name(created_at DESC);
```

### Debugging Queries

Check timestamp consistency across tables:

```sql
SELECT 
    'profiles' as table_name,
    COUNT(*) as total,
    COUNT(created_at) as has_created_at,
    COUNT(updated_at) as has_updated_at
FROM profiles
UNION ALL
SELECT 
    'documents' as table_name,
    COUNT(*) as total,
    COUNT(created_at) as has_created_at, 
    COUNT(updated_at) as has_updated_at
FROM documents;
```

## API Examples

### Python Supabase Client

```python
import os
from supabase import create_client
from app.models.supabase_models import SupabaseModelManager, Profile

# Initialize
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(supabase_url, supabase_key)
manager = SupabaseModelManager(supabase)

# Create profile with automatic timestamps
profile = await manager.create_record("profiles", Profile,
    id=uuid4(),
    email="user@example.com",
    full_name="John Smith",
    australian_state="NSW"
)

# Update profile with automatic updated_at
updated_profile = await manager.update_record("profiles", profile["id"], Profile,
    full_name="John Michael Smith",
    onboarding_completed=True
)

print(f"Created: {profile['created_at']}")
print(f"Updated: {updated_profile['updated_at']}")
```

### JavaScript/TypeScript

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(supabaseUrl, supabaseKey)

// Create with automatic timestamps
const { data: profile, error } = await supabase
  .from('profiles')
  .insert({
    id: crypto.randomUUID(),
    email: 'user@example.com',
    full_name: 'John Smith',
    australian_state: 'NSW'
    // created_at and updated_at set automatically
  })
  .select()

// Update with automatic updated_at
const { data: updated, error: updateError } = await supabase
  .from('profiles')
  .update({ 
    full_name: 'John Michael Smith',
    onboarding_completed: true
    // updated_at set automatically by trigger
  })
  .eq('id', profile[0].id)
  .select()
```

## Security Considerations

- Trigger function uses `SECURITY DEFINER` for consistent execution
- Timestamps are set server-side, preventing client manipulation
- Indexes support efficient querying without exposing internal data
- Database-level enforcement ensures audit trail integrity

## Support

For questions or issues with timestamp management:

1. Check the `timestamp_management_status` view
2. Review trigger configuration with `verify_timestamp_defaults()`
3. Use backfill functions for data consistency
4. Consult this documentation for best practices

---

*This system ensures reliable, automatic timestamp management across your entire Supabase database with zero maintenance overhead.*
# Contract ID vs Content Hash Architecture Analysis

## Current State Analysis

### Database Schema Overview
Both `contracts` and `contract_analyses` tables have:
- `id UUID PRIMARY KEY` (traditional relational ID)
- `content_hash TEXT UNIQUE NOT NULL` (content-based caching key)

### Usage Patterns Found

#### 1. **API Endpoints** - Use `contract_id` (UUID)
```
GET /api/contracts/{contract_id}/analysis
GET /api/contracts/{contract_id}/status  
DELETE /api/contracts/{contract_id}
```

#### 2. **WebSocket Sessions** - Use `contract_id` (UUID)
```python
contract_id = contract["id"]  # UUID from contracts table
```

#### 3. **Internal Lookups** - Use `content_hash` 
```python
# Analysis lookup by content_hash
result = db.table("contract_analyses").eq("content_hash", content_hash)
```

#### 4. **User Access Control** - Via document ownership
```python
# Verify access through documents.content_hash = user_id
doc_result = db.table("documents").eq("content_hash", content_hash).eq("user_id", user_id)
```

## Architectural Trade-offs

### Option A: Keep Both IDs ✅ Current
**Pros:**
- Clean API URLs (`/contracts/uuid` vs `/contracts/sha256hash`)  
- Stable external references (UUID doesn't change with content)
- Familiar REST patterns for frontend developers
- Clear separation: UUID for identity, hash for caching
- Better user experience (shorter, readable IDs)

**Cons:**
- Dual lookup complexity (UUID → content_hash → data)
- More database columns to maintain
- Potential confusion between the two IDs

### Option B: Content Hash Only ❌ Not Recommended
**Pros:**  
- Simplified schema (one less column per table)
- Direct lookup by content
- Natural deduplication

**Cons:**
- **API URLs become unwieldy**: `/contracts/a1b2c3d4e5f6...64chars.../analysis`
- **SHA-256 hashes leak information** about document content
- **Frontend complexity**: Dealing with 64-character identifiers
- **User experience**: Copy/paste URLs become problematic
- **Security concerns**: Content hashes might be guessable/enumerable

## Recommendation: **Keep Both IDs** 

### Optimal Architecture Design

```sql
-- Contracts table: UUID for external API, content_hash for internal caching
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),           -- External API identity
    content_hash TEXT UNIQUE NOT NULL,                        -- Internal caching key
    contract_type contract_type NOT NULL DEFAULT 'purchase_agreement',
    australian_state australian_state NOT NULL DEFAULT 'NSW',
    -- ... other fields
);

-- Contract analyses table: Same pattern
CREATE TABLE contract_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),           -- External API identity  
    content_hash TEXT UNIQUE NOT NULL,                        -- Internal caching key
    status analysis_status NOT NULL DEFAULT 'pending',
    -- ... analysis fields
);
```

### Usage Patterns (Optimized)

#### 1. **API Layer**: Use UUID for external interfaces
```python
@router.get("/{contract_id}/analysis") 
async def get_analysis(contract_id: str):  # UUID
    # Lookup: UUID → content_hash → analysis
    contract = await db.table("contracts").eq("id", contract_id).single()
    analysis = await db.table("contract_analyses").eq("content_hash", contract["content_hash"]).single()
```

#### 2. **Caching Layer**: Use content_hash for deduplication
```python
async def check_analysis_cache(content_hash: str):
    # Direct lookup by content_hash for cache hits
    return await db.table("contract_analyses").eq("content_hash", content_hash).single()
```

#### 3. **User Access Control**: Via document ownership + content_hash
```python
async def verify_access(contract_uuid: str, user_id: str):
    contract = await db.table("contracts").eq("id", contract_uuid).single()
    document = await db.table("documents").eq("content_hash", contract["content_hash"]).eq("user_id", user_id).single()
    return document is not None
```

## Implementation Benefits

### 🎯 **Best of Both Worlds**
- **Clean APIs**: `/contracts/550e8400-e29b-41d4-a716-446655440000/analysis`
- **Efficient Caching**: Direct content_hash lookups for shared resources  
- **User Privacy**: UUIDs don't leak document content information
- **Scalability**: Content-based deduplication still works perfectly

### 🔒 **Security & Privacy**
- UUIDs provide opaque, non-guessable identifiers
- Content hashes remain internal implementation detail
- User can't enumerate or guess other users' contracts

### 👥 **Developer Experience** 
- Familiar REST patterns (`/resource/{id}`)  
- Manageable URL lengths
- Easy debugging with readable UUIDs
- Clear separation of concerns

## Migration Strategy: **No Changes Needed**

The current schema is already optimal! The issue was just in the application code incorrectly trying to use `document_id` instead of the proper UUID → content_hash → analysis lookup pattern.

## Conclusion

**Keep both `id` and `content_hash` columns.** This hybrid approach provides:
- Clean external APIs (UUID)
- Efficient internal caching (content_hash) 
- Proper access control patterns
- Scalable shared resource architecture

The dual-ID pattern is a **well-established architectural practice** for systems that need both stable external identities and content-based optimization.
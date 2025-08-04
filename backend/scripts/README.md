# Real2.AI Database Migration Scripts

This directory contains scripts for managing Supabase database migrations, seeding, and setup for the Real2.AI platform.

## Quick Start

1. **Install uv** (if not already installed):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Or using pip
   pip install uv
   ```

2. **Initial Setup** (run once):
   ```bash
   ./setup_supabase.sh
   ```

3. **Set up Python environment**:
   ```bash
   # Install dependencies from pyproject.toml using uv
   uv sync --dev
   ```

3. **Set environment variables**:
   ```bash
   export SUPABASE_URL="http://127.0.0.1:54321"
   export SUPABASE_ANON_KEY="your_anon_key_here"
   export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key_here"
   export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
   ```

4. **Check Migration Status**:
   ```bash
   python3 migrate.py status
   ```

5. **Run Migrations**:
   ```bash
   python3 migrate.py up
   ```

6. **Create Demo User** (optional):
   ```bash
   # The demo user is automatically created during migrations
   # If you need to recreate it manually, use the simple script:
   export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
   python3 -c "
   import asyncio, asyncpg
   from datetime import datetime
   async def create_demo():
       conn = await asyncpg.connect('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
       demo_id = '00000000-0000-0000-0000-000000000001'
       now = datetime.now()
       await conn.execute('INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, raw_user_meta_data) VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (id) DO NOTHING', demo_id, 'demo@real2.ai', 'demo123456', now, now, now, '{\"full_name\": \"Demo User\"}')
       await conn.execute('INSERT INTO profiles (id, email, full_name, phone_number, australian_state, user_type, subscription_status, credits_remaining, organization) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) ON CONFLICT (id) DO UPDATE SET full_name = EXCLUDED.full_name', demo_id, 'demo@real2.ai', 'Demo User', '+61 2 9876 5432', 'NSW', 'investor', 'premium', 50, 'Real2.AI Demo')
       await conn.close()
       print('✅ Demo user created: demo@real2.ai / demo123456')
   asyncio.run(create_demo())
   "
   ```

## Scripts Overview

### 🚀 setup_supabase.sh
One-time setup script that:
- Initializes Supabase local development environment
- Starts Supabase services (PostgreSQL, Auth, Storage, etc.)
- Runs all database migrations
- Optionally seeds database with sample data
- Creates/updates .env file with connection details

**Usage:**
```bash
./setup_supabase.sh
```

### 🗄️ migrate.py
Database migration management with version tracking and rollback protection.

**Commands:**
```bash
# Check current migration status
python3 migrate.py status

# Apply all pending migrations
python3 migrate.py up

# Apply migrations up to specific version
python3 migrate.py up --target 20240101000002

# Create new migration file
python3 migrate.py create --name "add_user_preferences"

# Reset database (DANGEROUS - requires ALLOW_DATABASE_RESET=true)
python3 migrate.py reset
```

**Features:**
- ✅ Version tracking and checksum validation
- ✅ Transaction-based migration execution
- ✅ Detailed logging and error reporting
- ✅ Migration file templates
- ✅ Rollback protection (no destructive rollbacks)

### 🌱 seed_database.py
Populates database with sample data for development and testing.

**Usage:**
```bash
# Seed database with sample data
python3 seed_database.py

# Reset and reseed all data
python3 seed_database.py --reset
```

**Sample Data Includes:**
- Demo user profiles (investor, agent, buyer)
- Sample contract documents
- Contract analysis results
- Usage logs and billing data
- Property information
- Subscription data

## Migration Files

Located in `../supabase/migrations/`:

### 20240101000000_initial_schema.sql
- Core database tables and relationships
- Custom types and enums
- Performance indexes
- Data validation constraints

### 20240101000001_security_policies.sql
- Row Level Security (RLS) policies
- User access controls
- Service role permissions
- Security functions for credit management

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'asyncpg'**
   ```bash
   # Solution: Install dependencies from pyproject.toml using uv
   uv sync --dev
   ```

2. **uv command not found**
   ```bash
   # Install uv first
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Then run
   uv sync --dev
   ```

2. **Foreign key constraint violations**
   ```bash
   # Solution: Reset database and run migrations
   export ALLOW_DATABASE_RESET=true
   python3 migrate.py reset
   ```

3. **Demo user not working**
   ```bash
   # Solution: Check if demo user exists
   python3 -c "
   import asyncio, asyncpg
   async def check():
       conn = await asyncpg.connect('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
       result = await conn.fetchrow('SELECT * FROM profiles WHERE email = $1', 'demo@real2.ai')
       print('Demo user exists:', result is not None)
       await conn.close()
   asyncio.run(check())
   "
   ```

### Demo User Credentials

- **Email**: `demo@real2.ai`
- **Password**: `demo123456`
- **User ID**: `00000000-0000-0000-0000-000000000001`

### 20240101000002_functions_triggers.sql
- Database functions and triggers
- Automated timestamp updates
- Australian postcode validation
- Analysis progress tracking
- Business logic functions

### 20240101000003_seed_data.sql
- Subscription plans
- Australian reference data
- Contract type definitions
- System configuration
- Default settings

### 20240101000004_storage_setup.sql
- Supabase Storage bucket configuration
- File upload policies
- Storage quotas and validation
- File management functions

## Environment Variables

Required environment variables (set by setup script):

```bash
# Supabase Configuration
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres

# Application Settings
ENVIRONMENT=development
DEBUG=true
OPENAI_API_KEY=your_openai_key

# Safety Settings
ALLOW_DATABASE_RESET=true  # Only for development
```

## Database Schema Overview

### Core Tables
- **profiles** - User profiles extending auth.users
- **documents** - Uploaded contract files
- **contracts** - Contract metadata and terms
- **contract_analyses** - AI analysis results
- **usage_logs** - Credit usage and billing tracking

### Reference Tables  
- **subscription_plans** - Available subscription tiers
- **australian_states_ref** - State reference data
- **contract_types_ref** - Contract type definitions
- **property_types_ref** - Property classification

### System Tables
- **schema_migrations** - Migration version tracking
- **analysis_progress** - Real-time progress tracking
- **maintenance_log** - System maintenance history

## Security Features

- **Row Level Security (RLS)** - Users can only access their own data
- **Service Role Functions** - Admin operations with proper authentication
- **File Upload Validation** - Size limits, type checking, secure storage
- **Credit Management** - Atomic operations preventing race conditions
- **Audit Logging** - Comprehensive usage tracking

## Development Workflow

1. **Start Development Environment**:
   ```bash
   ./setup_supabase.sh
   ```

2. **Make Schema Changes**:
   ```bash
   python3 migrate.py create --name "your_migration_name"
   # Edit the generated migration file
   python3 migrate.py up
   ```

3. **Test with Sample Data**:
   ```bash
   python3 seed_database.py
   ```

4. **Check Status**:
   ```bash
   python3 migrate.py status
   supabase status
   ```

## Troubleshooting

### Common Issues

**Migration fails with "relation already exists"**:
- Check if migration was partially applied
- Use `python3 migrate.py status` to see current state
- Manually fix conflicts or reset database for development

**Supabase won't start**:
```bash
supabase stop
supabase start
```

**Connection errors**:
- Verify Supabase is running: `supabase status`
- Check .env file has correct connection details
- Ensure required Python packages are installed

**Permission denied on scripts**:
```bash
chmod +x setup_supabase.sh
chmod +x migrate.py
```

### Reset Development Database

⚠️ **DANGER**: This will delete all data!

```bash
# Set environment variable
export ALLOW_DATABASE_RESET=true

# Reset database and re-run migrations
python3 migrate.py reset

# Or reset Supabase completely
supabase stop
supabase start
./setup_supabase.sh
```

## Production Deployment

For production deployments:

1. **Remove development settings**:
   - Set `ALLOW_DATABASE_RESET=false` or remove entirely
   - Use production database URL
   - Set `ENVIRONMENT=production`

2. **Run migrations**:
   ```bash
   python3 migrate.py up
   ```

3. **Do NOT run seed script in production**

## Support

For issues with database migrations or setup:

1. Check the migration status: `python3 migrate.py status`
2. Review Supabase logs: `supabase logs`
3. Verify environment variables are correct
4. Ensure all dependencies are installed

The migration system is designed to be safe and recoverable. If you encounter issues, the migration tracking table maintains a complete history of what was applied and when.
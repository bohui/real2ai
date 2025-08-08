-- Row Level Security policies for Real2.AI
-- Ensures users can only access their own data

-- Enable RLS on user-specific and possession-gated tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
-- Keep property_data without RLS (shared cache), guarded via revokes/RPCs
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
-- analysis_progress may remain without RLS if shared; restrict via RPC/possession flows

-- Profiles policies
CREATE POLICY "Users can view own profile" 
    ON profiles FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" 
    ON profiles FOR UPDATE 
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile on signup" 
    ON profiles FOR INSERT 
    WITH CHECK (auth.uid() = id);

-- Documents policies
CREATE POLICY "Users can view own documents" 
    ON documents FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents" 
    ON documents FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own documents" 
    ON documents FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents" 
    ON documents FOR DELETE 
    USING (auth.uid() = user_id);

-- Contracts policies (possession-gated SELECT by content_hash)
DROP POLICY IF EXISTS "read_if_user_has_hash" ON contracts;
CREATE POLICY "read_if_user_has_hash"
    ON contracts FOR SELECT
    USING (
        -- Service role can access all contracts
        auth.jwt() ->> 'role' = 'service_role'
        OR
        -- Users can access contracts they have access to through user_contract_views or documents
        EXISTS (
            SELECT 1 FROM user_contract_views v
            WHERE v.user_id = auth.uid()
              AND v.content_hash = contracts.content_hash
        )
        OR EXISTS (
            SELECT 1 FROM documents d
            WHERE d.user_id = auth.uid()
              AND d.content_hash = contracts.content_hash
        )
    );

-- CREATE POLICY "Users can delete own contracts" 
--     ON contracts FOR DELETE 
--     USING (auth.uid() = user_id);

-- Contract analyses policies (possession-gated SELECT by content_hash)
DROP POLICY IF EXISTS "read_if_user_has_hash" ON contract_analyses;
CREATE POLICY "read_if_user_has_hash"
    ON contract_analyses FOR SELECT
    USING (
        -- Service role can access all contract analyses
        auth.jwt() ->> 'role' = 'service_role'
        OR
        -- Users can access analyses they have access to through user_contract_views or documents
        EXISTS (
            SELECT 1 FROM user_contract_views v
            WHERE v.user_id = auth.uid()
              AND v.content_hash = contract_analyses.content_hash
        )
        OR EXISTS (
            SELECT 1 FROM documents d
            WHERE d.user_id = auth.uid()
              AND d.content_hash = contract_analyses.content_hash
        )
    );

-- Usage logs policies
CREATE POLICY "Users can view own usage logs" 
    ON usage_logs FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Service can insert usage logs" 
    ON usage_logs FOR INSERT 
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role' OR auth.uid() = user_id);

-- Property data remains shared (no RLS), access controlled via RPCs and revokes below

-- User subscriptions policies
CREATE POLICY "Users can view own subscriptions" 
    ON user_subscriptions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Service can manage subscriptions" 
    ON user_subscriptions FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Analysis progress policies - DISABLED for caching efficiency
-- RLS disabled on analysis_progress table to enable cross-user progress sharing
-- Access control handled at application level
-- CREATE POLICY "Users can view own analysis progress" 
--     ON analysis_progress FOR SELECT 
--     USING (auth.uid() = user_id);

-- CREATE POLICY "Service can manage analysis progress" 
--     ON analysis_progress FOR ALL 
--     USING (auth.jwt() ->> 'role' = 'service_role');

-- Analysis progress detailed view policies
-- Note: RLS cannot be enabled on views, but the view inherits security from underlying tables
-- The view will automatically respect the RLS policies on analysis_progress table

-- Subscription plans are publicly readable (no RLS needed)
-- This allows users to see available plans without authentication
CREATE POLICY "Anyone can view active subscription plans" 
    ON subscription_plans FOR SELECT 
    USING (active = true);

-- Create security definer functions for admin operations
CREATE OR REPLACE FUNCTION get_user_analytics(target_user_id UUID)
RETURNS JSON
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
    result JSON;
BEGIN
    -- Only allow service role to access this function
    IF auth.jwt() ->> 'role' != 'service_role' THEN
        RAISE EXCEPTION 'Access denied';
    END IF;

    SELECT json_build_object(
        'total_documents', COUNT(d.id),
        'total_analyses', COUNT(ca.id),
        'credits_used', COALESCE(SUM(ul.credits_used), 0),
        'avg_risk_score', COALESCE(AVG(ca.overall_risk_score), 0),
        'last_activity', MAX(GREATEST(d.created_at, ca.created_at))
    ) INTO result
    FROM profiles p
    LEFT JOIN documents d ON p.id = d.user_id
    LEFT JOIN contract_analyses ca ON p.id = ca.user_id
    LEFT JOIN usage_logs ul ON p.id = ul.user_id
    WHERE p.id = target_user_id
    GROUP BY p.id;

    RETURN result;
END;
$$;

-- Function to safely update user credits (prevents race conditions)
CREATE OR REPLACE FUNCTION update_user_credits(
    target_user_id UUID,
    credit_change INTEGER,
    action_description TEXT DEFAULT 'Credit adjustment'
)
RETURNS INTEGER
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
    new_credits INTEGER;
    current_credits INTEGER;
BEGIN
    -- Lock the user record to prevent concurrent updates
    SELECT credits_remaining INTO current_credits
    FROM profiles
    WHERE id = target_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User not found';
    END IF;

    -- Calculate new credits (cannot go below 0)
    new_credits := GREATEST(0, current_credits + credit_change);

    -- Update the user's credits
    UPDATE profiles
    SET credits_remaining = new_credits,
        updated_at = NOW()
    WHERE id = target_user_id;

    -- Log the credit change
    INSERT INTO usage_logs (user_id, action_type, credits_used, credits_remaining, metadata)
    VALUES (
        target_user_id,
        action_description,
        -credit_change, -- Negative for credits added, positive for credits used
        new_credits,
        json_build_object('previous_credits', current_credits, 'credit_change', credit_change)
    );

    RETURN new_credits;
END;
$$;

-- Function to check if user has sufficient credits
CREATE OR REPLACE FUNCTION check_user_credits(
    target_user_id UUID,
    required_credits INTEGER DEFAULT 1
)
RETURNS BOOLEAN
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
    current_credits INTEGER;
BEGIN
    SELECT credits_remaining INTO current_credits
    FROM profiles
    WHERE id = target_user_id;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    RETURN current_credits >= required_credits;
END;
$$;

-- ------------------------------------------------------------
-- Revoke direct access to shared/derived tables for anon/authenticated
-- ------------------------------------------------------------

DO $$
BEGIN
  -- contract_analyses
  IF EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'contract_analyses'
  ) THEN
    EXECUTE 'REVOKE ALL ON TABLE public.contract_analyses FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.contract_analyses FROM authenticated';
  END IF;

  -- contracts
  IF EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'contracts'
  ) THEN
    EXECUTE 'REVOKE ALL ON TABLE public.contracts FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.contracts FROM authenticated';
  END IF;

  -- property_data (shared cache table)
  IF EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'property_data'
  ) THEN
    EXECUTE 'REVOKE ALL ON TABLE public.property_data FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.property_data FROM authenticated';
  END IF;
END $$;

-- After revokes, grant SELECT to authenticated so RLS policies can apply
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'contracts'
  ) THEN
    EXECUTE 'GRANT SELECT ON TABLE public.contracts TO authenticated';
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'contract_analyses'
  ) THEN
    EXECUTE 'GRANT SELECT ON TABLE public.contract_analyses TO authenticated';
  END IF;
END $$;

COMMENT ON POLICY "read_if_user_has_hash" ON public.contract_analyses IS 'Allow reading derived analysis only if the user has possession (document or view) for the same content hash';
COMMENT ON POLICY "read_if_user_has_hash" ON public.contracts IS 'Allow reading contract rows only if the user has possession (document or view) for the same content hash';
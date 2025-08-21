-- Application RPCs to support backend calls

-- Simple health check RPC
CREATE OR REPLACE FUNCTION public.health_check()
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN jsonb_build_object('status', 'ok', 'timestamp', NOW());
END;
$$;

GRANT EXECUTE ON FUNCTION public.health_check() TO anon, authenticated, service_role;

-- Wrapper for Postgres version() to allow RPC call
CREATE OR REPLACE FUNCTION public.version()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
  SELECT pg_catalog.version();
$$;

GRANT EXECUTE ON FUNCTION public.version() TO authenticated, service_role;

-- Ensure a storage bucket exists (id=name)
CREATE OR REPLACE FUNCTION public.ensure_bucket_exists(bucket_name TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  existed BOOLEAN := FALSE;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM storage.buckets b WHERE b.id = bucket_name
  ) THEN
    INSERT INTO storage.buckets (id, name, public)
    VALUES (bucket_name, bucket_name, false)
    ON CONFLICT (id) DO NOTHING;
  ELSE
    existed := TRUE;
  END IF;
  RETURN jsonb_build_object('status', 'ok', 'existed', existed);
END;
$$;

GRANT EXECUTE ON FUNCTION public.ensure_bucket_exists(TEXT) TO service_role, authenticated;

-- Document statistics (lightweight)
CREATE OR REPLACE FUNCTION public.get_document_statistics()
RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
  SELECT jsonb_build_object(
    'total_documents', (SELECT COUNT(*) FROM public.documents),
    'total_contracts', (SELECT COUNT(*) FROM public.contracts),
    'total_analyses', (SELECT COUNT(*) FROM public.analyses)
  );
$$;

GRANT EXECUTE ON FUNCTION public.get_document_statistics() TO service_role, authenticated;

-- System analytics (placeholder)
CREATE OR REPLACE FUNCTION public.generate_system_analytics()
RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
  SELECT jsonb_build_object(
    'generated_at', NOW(),
    'documents', (SELECT COUNT(*) FROM public.documents),
    'analyses', (SELECT COUNT(*) FROM public.analyses)
  );
$$;

GRANT EXECUTE ON FUNCTION public.generate_system_analytics() TO service_role;

-- Cleanup expired documents (placeholder)
CREATE OR REPLACE FUNCTION public.cleanup_expired_documents(days_old INTEGER)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  -- Implement actual cleanup logic as needed
  RETURN jsonb_build_object('deleted_count', 0);
END;
$$;

GRANT EXECUTE ON FUNCTION public.cleanup_expired_documents(INTEGER) TO service_role;

-- Process contract cache hit: create minimal user-scoped records and return ids
CREATE OR REPLACE FUNCTION public.process_contract_cache_hit(
  p_user_id UUID,
  p_content_hash TEXT,
  p_filename TEXT,
  p_file_size BIGINT,
  p_mime_type TEXT,
  p_property_address TEXT
)
RETURNS TABLE(document_id UUID, analysis_id UUID, view_id UUID)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_doc_id UUID;
  v_analysis_id UUID;
  v_view_id UUID;
BEGIN
  -- Ensure a contract row exists
  INSERT INTO public.contracts (content_hash, contract_type, australian_state, property_address)
  VALUES (p_content_hash, 'purchase_agreement', 'NSW', p_property_address)
  ON CONFLICT (content_hash) DO NOTHING;

  -- Create a minimal user document
  INSERT INTO public.documents (
    user_id, original_filename, storage_path, file_type, file_size, content_hash,
    processing_status
  ) VALUES (
    p_user_id, COALESCE(p_filename, 'Cached Document'), '', COALESCE(p_mime_type, 'application/pdf'), p_file_size,
    p_content_hash, 'analysis_complete'
  ) RETURNING id INTO v_doc_id;

  -- Get existing analysis or create a placeholder
  SELECT id INTO v_analysis_id FROM public.analyses WHERE content_hash = p_content_hash LIMIT 1;
  
  IF v_analysis_id IS NULL THEN
    INSERT INTO public.analyses (content_hash, agent_version, status)
    VALUES (p_content_hash, '1.0', 'pending')
    RETURNING id INTO v_analysis_id;
  END IF;

  -- Record a user view for history
  INSERT INTO public.user_contract_views (user_id, content_hash, property_address, analysis_id)
  VALUES (p_user_id, p_content_hash, p_property_address, v_analysis_id)
  RETURNING id INTO v_view_id;

  document_id := v_doc_id;
  analysis_id := v_analysis_id;
  view_id := v_view_id;
  RETURN NEXT;
END;
$$;

GRANT EXECUTE ON FUNCTION public.process_contract_cache_hit(UUID, TEXT, TEXT, BIGINT, TEXT, TEXT) TO service_role;

-- User contract history
CREATE OR REPLACE FUNCTION public.get_user_contract_history(p_user_id UUID)
RETURNS TABLE(
  view_id UUID,
  content_hash TEXT,
  property_address TEXT,
  analysis_id UUID,
  viewed_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
AS $$
  SELECT ucv.id, ucv.content_hash, ucv.property_address, ucv.analysis_id, ucv.viewed_at
  FROM public.user_contract_views ucv
  WHERE ucv.user_id = p_user_id
  ORDER BY ucv.viewed_at DESC;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_contract_history(UUID) TO authenticated, service_role;

-- User property history
CREATE OR REPLACE FUNCTION public.get_user_property_history(p_user_id UUID)
RETURNS TABLE(
  view_id UUID,
  property_hash TEXT,
  property_address TEXT,
  viewed_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
AS $$
  SELECT upv.id, upv.property_hash, upv.property_address, upv.viewed_at
  FROM public.user_property_views upv
  WHERE upv.user_id = p_user_id
  ORDER BY upv.viewed_at DESC;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_property_history(UUID) TO authenticated, service_role;

-- Optimized single-access check
CREATE OR REPLACE FUNCTION public.get_user_contract_access_optimized(
  p_user_id UUID,
  p_contract_id UUID
)
RETURNS TABLE(
  contract_id UUID,
  content_hash TEXT,
  has_access BOOLEAN,
  access_source TEXT,
  analysis_id UUID,
  analysis_status TEXT,
  analysis_created_at TIMESTAMPTZ,
  analysis_updated_at TIMESTAMPTZ,
  processing_time DECIMAL,
  error_message TEXT,
  analysis_metadata JSONB
)
LANGUAGE sql
STABLE
AS $$
  WITH contract_row AS (
    SELECT c.id, c.content_hash FROM public.contracts c WHERE c.id = p_contract_id
  ),
  user_hashes AS (
    SELECT d.content_hash FROM public.documents d WHERE d.user_id = p_user_id AND d.content_hash IS NOT NULL
    UNION
    SELECT v.content_hash FROM public.user_contract_views v WHERE v.user_id = p_user_id
  ),
  latest_analysis AS (
    SELECT a.* FROM public.analyses a
    JOIN contract_row cr ON cr.content_hash = a.content_hash
    ORDER BY a.created_at DESC
    LIMIT 1
  )
  SELECT 
    cr.id AS contract_id,
    cr.content_hash,
    (cr.content_hash IN (SELECT content_hash FROM user_hashes)) AS has_access,
    CASE WHEN cr.content_hash IN (SELECT content_hash FROM user_hashes) THEN 'optimized' ELSE 'none' END AS access_source,
    la.id AS analysis_id,
    la.status::text AS analysis_status,
    la.created_at AS analysis_created_at,
    la.updated_at AS analysis_updated_at,
    NULL::DECIMAL AS processing_time,
    (la.error_details->>'message') AS error_message,
    la.error_details AS analysis_metadata
  FROM contract_row cr
  LEFT JOIN latest_analysis la ON TRUE;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_contract_access_optimized(UUID, UUID) TO authenticated, service_role;

-- Bulk access
CREATE OR REPLACE FUNCTION public.get_user_contracts_bulk_access(
  p_user_id UUID,
  p_limit INTEGER DEFAULT 50
)
RETURNS TABLE(
  contract_id UUID,
  content_hash TEXT,
  analysis_id UUID,
  analysis_status TEXT,
  analysis_created_at TIMESTAMPTZ,
  analysis_updated_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
AS $$
  WITH user_hashes AS (
    SELECT d.content_hash FROM public.documents d WHERE d.user_id = p_user_id AND d.content_hash IS NOT NULL
    UNION
    SELECT v.content_hash FROM public.user_contract_views v WHERE v.user_id = p_user_id
  ),
  contracts_for_user AS (
    SELECT c.* FROM public.contracts c
    WHERE c.content_hash IN (SELECT content_hash FROM user_hashes)
    ORDER BY c.created_at DESC
    LIMIT p_limit
  )
  SELECT c.id AS contract_id,
         c.content_hash,
         ca.id AS analysis_id,
         ca.status::text AS analysis_status,
         ca.created_at AS analysis_created_at,
         ca.updated_at AS analysis_updated_at
  FROM contracts_for_user c
  LEFT JOIN LATERAL (
    SELECT * FROM public.analyses a
    WHERE a.content_hash = c.content_hash
    ORDER BY a.created_at DESC
    LIMIT 1
  ) ca ON TRUE;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_contracts_bulk_access(UUID, INTEGER) TO authenticated, service_role;

-- Contract performance report (placeholder)
CREATE OR REPLACE FUNCTION public.generate_contract_performance_report()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
  SELECT 'Contract performance report generation is not implemented yet'::text;
$$;

GRANT EXECUTE ON FUNCTION public.generate_contract_performance_report() TO service_role, authenticated;

-- Evaluation analytics (placeholders)
CREATE OR REPLACE FUNCTION public.get_model_comparison_for_user(
  user_id UUID,
  dataset_filter UUID DEFAULT NULL,
  date_from_filter TIMESTAMPTZ DEFAULT NULL,
  date_to_filter TIMESTAMPTZ DEFAULT NULL
)
RETURNS TABLE(
  model_name VARCHAR(255),
  total_evaluations BIGINT,
  avg_overall_score DECIMAL(5,4),
  avg_response_time_ms DECIMAL(10,2),
  avg_token_usage DECIMAL(10,2),
  last_evaluation TIMESTAMPTZ
)
LANGUAGE sql
STABLE
AS $$
  SELECT NULL::varchar, 0::bigint, 0.0::decimal, 0.0::decimal, 0.0::decimal, NULL::timestamptz
  WHERE FALSE;
$$;

GRANT EXECUTE ON FUNCTION public.get_model_comparison_for_user(UUID, UUID, TIMESTAMPTZ, TIMESTAMPTZ) TO authenticated;

CREATE OR REPLACE FUNCTION public.get_user_evaluation_stats(user_id UUID)
RETURNS TABLE(
  total_prompts BIGINT,
  total_datasets BIGINT,
  total_jobs BIGINT,
  total_evaluations BIGINT,
  avg_overall_score DECIMAL(5,4),
  first_evaluation TIMESTAMPTZ,
  last_evaluation TIMESTAMPTZ
)
LANGUAGE sql
STABLE
AS $$
  SELECT 0::bigint, 0::bigint, 0::bigint, 0::bigint, 0.0::decimal, NULL::timestamptz, NULL::timestamptz;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_evaluation_stats(UUID) TO authenticated;

-- No-op rebuild function for simplified architecture
CREATE OR REPLACE FUNCTION public.rebuild_contract_cache(
  min_confidence FLOAT DEFAULT 0.7,
  days_back INTEGER DEFAULT 30,
  max_entries INTEGER DEFAULT 1000
)
RETURNS INTEGER
LANGUAGE sql
STABLE
AS $$
  SELECT 0::int;
$$;

GRANT EXECUTE ON FUNCTION public.rebuild_contract_cache(FLOAT, INTEGER, INTEGER) TO service_role;



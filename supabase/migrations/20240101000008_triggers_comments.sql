-- Triggers and comments

CREATE TRIGGER update_property_data_updated_at BEFORE UPDATE ON property_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_progress_updated_at_trigger
    BEFORE UPDATE ON analysis_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION calculate_analysis_progress_elapsed_time()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.step_completed_at IS NOT NULL AND OLD.step_completed_at IS NULL THEN
        NEW.total_elapsed_seconds = COALESCE(OLD.total_elapsed_seconds, 0) + 
            EXTRACT(EPOCH FROM (NEW.step_completed_at - COALESCE(NEW.step_started_at, NEW.created_at)))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_analysis_progress_elapsed_time_trigger
    BEFORE UPDATE ON analysis_progress
    FOR EACH ROW
    EXECUTE FUNCTION calculate_analysis_progress_elapsed_time();

CREATE TRIGGER update_task_registry_updated_at 
    BEFORE UPDATE ON task_registry
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recovery_queue_updated_at
    BEFORE UPDATE ON recovery_queue  
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE analysis_progress IS 'Real-time progress tracking for document analysis and contract processing';
COMMENT ON COLUMN analysis_progress.content_hash IS 'Content hash linking to shared analysis resources';
COMMENT ON COLUMN analysis_progress.current_step IS 'Current processing step (e.g., text_extraction, contract_analysis)';
COMMENT ON COLUMN analysis_progress.progress_percent IS 'Progress percentage from 0 to 100';
COMMENT ON COLUMN analysis_progress.step_description IS 'Human-readable description of current step';
COMMENT ON COLUMN analysis_progress.estimated_completion_minutes IS 'Estimated minutes until completion';
COMMENT ON COLUMN analysis_progress.total_elapsed_seconds IS 'Total time elapsed since analysis started';
COMMENT ON COLUMN analysis_progress.status IS 'Overall status: in_progress, completed, failed, or cancelled';
COMMENT ON COLUMN analysis_progress.error_message IS 'Error message if analysis fails';
COMMENT ON COLUMN analysis_progress.metadata IS 'Additional metadata for progress tracking';


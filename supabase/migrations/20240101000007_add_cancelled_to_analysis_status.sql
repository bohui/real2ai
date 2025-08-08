-- Add 'cancelled' to the analysis_status enum
-- This fixes the error where the application tries to set status to 'cancelled' 
-- but the enum doesn't include this value

ALTER TYPE analysis_status ADD VALUE 'cancelled'; 
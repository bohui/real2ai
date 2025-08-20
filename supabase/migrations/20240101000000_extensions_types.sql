-- Initial split migration: extensions and types
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE australian_state AS ENUM ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT');
CREATE TYPE user_type AS ENUM ('buyer', 'investor', 'agent');
CREATE TYPE subscription_status AS ENUM ('free', 'basic', 'premium', 'enterprise');
CREATE TYPE contract_type AS ENUM ('purchase_agreement', 'lease_agreement', 'option_to_purchase', 'unknown');
CREATE TYPE purchase_method AS ENUM ('standard', 'off_plan', 'auction', 'private_treaty', 'tender', 'expression_of_interest');
CREATE TYPE use_category AS ENUM ('residential', 'commercial', 'industrial', 'retail');
CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'basic_complete', 'analysis_pending', 'analysis_complete', 'failed');
CREATE TYPE content_type AS ENUM ('text', 'diagram', 'table', 'signature', 'mixed', 'empty');
CREATE TYPE diagram_type AS ENUM ('site_plan', 'sewer_diagram', 'flood_map', 'bushfire_map', 'title_plan', 'survey_diagram', 'floor_plan', 'elevation', 'unknown');
CREATE TYPE entity_type AS ENUM ('address', 'property_reference', 'date', 'financial_amount', 'party_name', 'legal_reference', 'contact_info', 'property_details');
CREATE TYPE analysis_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');


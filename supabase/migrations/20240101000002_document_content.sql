-- Shared and user-scoped document content

CREATE TABLE document_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    content_summary TEXT,
    text_content TEXT,
    text_length INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    content_types TEXT[],
    primary_content_type content_type DEFAULT 'empty',
    extraction_confidence FLOAT DEFAULT 0.0,
    content_quality_score FLOAT DEFAULT 0.0,
    has_header BOOLEAN DEFAULT FALSE,
    has_footer BOOLEAN DEFAULT FALSE,
    has_signatures BOOLEAN DEFAULT FALSE,
    has_handwriting BOOLEAN DEFAULT FALSE,
    has_diagrams BOOLEAN DEFAULT FALSE,
    has_tables BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_method VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE document_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL,
    page_id UUID REFERENCES document_pages(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    entity_type entity_type NOT NULL,
    entity_value TEXT NOT NULL,
    normalized_value TEXT,
    context TEXT,
    confidence FLOAT DEFAULT 0.0,
    extraction_method VARCHAR(100),
    position_data JSONB,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE document_diagrams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    content_hash TEXT,
    page_id UUID REFERENCES document_pages(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    diagram_type diagram_type DEFAULT 'unknown',
    classification_confidence FLOAT DEFAULT 0.0,
    extracted_image_path VARCHAR(1024),
    basic_analysis_completed BOOLEAN DEFAULT FALSE,
    detailed_analysis_completed BOOLEAN DEFAULT FALSE,
    basic_analysis JSONB,
    image_quality_score FLOAT DEFAULT 0.0,
    clarity_score FLOAT DEFAULT 0.0,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    basic_analysis_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS unique_document_diagrams_doc_page_type
    ON document_diagrams(document_id, page_number, diagram_type);

CREATE TABLE document_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE NOT NULL,
    analysis_type VARCHAR(100) DEFAULT 'contract_analysis',
    analysis_version VARCHAR(50) DEFAULT 'v1.0',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    current_step VARCHAR(100),
    detailed_entities JSONB,
    diagram_analyses JSONB,
    compliance_results JSONB,
    risk_assessment JSONB,
    recommendations JSONB,
    overall_confidence FLOAT DEFAULT 0.0,
    analysis_quality_score FLOAT DEFAULT 0.0,
    processing_time_seconds FLOAT DEFAULT 0.0,
    langgraph_workflow_id VARCHAR(255),
    analysis_errors JSONB,
    analysis_warnings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


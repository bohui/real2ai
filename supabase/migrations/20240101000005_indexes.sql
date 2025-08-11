-- Core indexes
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_australian_state ON profiles(australian_state);
CREATE INDEX idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX idx_profiles_onboarding_completed ON profiles(onboarding_completed);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_australian_state ON documents(australian_state);
CREATE INDEX idx_documents_contract_type ON documents(contract_type);
CREATE INDEX idx_documents_has_diagrams ON documents(has_diagrams);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

CREATE INDEX idx_contracts_content_hash ON contracts(content_hash);
CREATE INDEX idx_contracts_type_state ON contracts(contract_type, australian_state);

CREATE INDEX idx_contract_analyses_content_hash ON contract_analyses(content_hash);
CREATE INDEX idx_contract_analyses_status ON contract_analyses(status);
CREATE INDEX idx_contract_analyses_timestamp ON contract_analyses(analysis_timestamp DESC);
CREATE INDEX idx_contract_analyses_risk_score ON contract_analyses(overall_risk_score);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_action_type ON usage_logs(action_type);

CREATE INDEX idx_property_data_location ON property_data(suburb, state, postcode);
CREATE INDEX idx_property_data_property_type ON property_data(property_type);
CREATE INDEX idx_property_data_property_hash ON property_data(property_hash);

CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_stripe_id ON user_subscriptions(stripe_subscription_id);

CREATE INDEX idx_analysis_progress_content_hash ON analysis_progress(content_hash);
CREATE INDEX idx_analysis_progress_user ON analysis_progress(user_id);
CREATE INDEX idx_analysis_progress_user_id ON analysis_progress(user_id);
CREATE INDEX idx_analysis_progress_status ON analysis_progress(status);
CREATE INDEX idx_analysis_progress_created_at ON analysis_progress(created_at);

CREATE INDEX idx_document_pages_content_hash ON document_pages(content_hash);
CREATE INDEX idx_document_pages_document_id ON document_pages(document_id);
CREATE INDEX idx_document_pages_page_number ON document_pages(page_number);
CREATE INDEX idx_document_pages_content_type ON document_pages(primary_content_type);

CREATE INDEX idx_document_entities_content_hash ON document_entities(content_hash);
CREATE INDEX idx_document_entities_page_id ON document_entities(page_id);
CREATE INDEX idx_document_entities_page_number ON document_entities(page_number);
CREATE INDEX idx_document_entities_type ON document_entities(entity_type);

CREATE INDEX idx_document_diagrams_document_id ON document_diagrams(document_id);
CREATE INDEX idx_document_diagrams_page_id ON document_diagrams(page_id);
CREATE INDEX idx_document_diagrams_page_number ON document_diagrams(page_number);
CREATE INDEX idx_document_diagrams_type ON document_diagrams(diagram_type);

CREATE INDEX idx_document_analyses_document_id ON document_analyses(document_id);
CREATE INDEX idx_document_analyses_status ON document_analyses(status);
CREATE INDEX idx_document_analyses_analysis_type ON document_analyses(analysis_type);

CREATE INDEX idx_analysis_progress_active ON analysis_progress(content_hash, user_id, updated_at) 
WHERE status = 'in_progress';

CREATE INDEX idx_documents_user_status ON documents(user_id, processing_status);


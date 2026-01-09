-- Initialize PostgreSQL with required extensions for Krystal Le Agent

-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable full-text search (built-in, but ensure it's ready)
-- No extension needed, but we can create text search configurations

-- Create custom text search configuration for tax documents
-- This helps with searching tax-specific terms
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'tax_english') THEN
        CREATE TEXT SEARCH CONFIGURATION tax_english (COPY = english);
    END IF;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE lecpa_agent TO lecpa;

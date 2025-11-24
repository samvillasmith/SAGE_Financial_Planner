-- pgvector Extension and Documents Table
-- Version: 002
-- Description: Enable pgvector for semantic search, replacing S3 Vectors

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table for storing text with embeddings
-- Used for financial research, market insights, and other searchable content
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    text TEXT NOT NULL,
    embedding vector(384),  -- Matches SageMaker all-MiniLM-L6-v2 model
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create HNSW index for fast approximate nearest neighbor search
-- HNSW offers better query performance than IVFFlat for most use cases
CREATE INDEX IF NOT EXISTS idx_documents_embedding
ON documents USING hnsw (embedding vector_cosine_ops);

-- Index on metadata for filtered searches
CREATE INDEX IF NOT EXISTS idx_documents_metadata
ON documents USING gin (metadata);

-- Index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_documents_created_at
ON documents (created_at DESC);

-- Add update trigger for updated_at
CREATE TRIGGER update_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE documents IS 'Vector storage for semantic search - replaces S3 Vectors';
COMMENT ON COLUMN documents.embedding IS '384-dimensional vector from all-MiniLM-L6-v2';
COMMENT ON COLUMN documents.metadata IS 'Flexible metadata: source, category, symbol, etc.';

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Stores user profile information';
COMMENT ON COLUMN users.id IS 'User ID from auth service, serves as primary key';
COMMENT ON COLUMN users.email IS 'User email address';


-- Create documents table 
CREATE TABLE documents (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    embedding VECTOR(1536) NOT NULL,
    content TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE documents IS 'Stores document chunks with vector embeddings for semantic search';
COMMENT ON COLUMN documents.chunk_id IS 'Unique identifier for each document chunk';
COMMENT ON COLUMN documents.document_id IS 'Unique identifier for each document';
COMMENT ON COLUMN documents.embedding IS 'Vector embedding for semantic search';
COMMENT ON COLUMN documents.content IS 'Actual text content of the document chunk';
COMMENT ON COLUMN documents.title IS 'Title of the document';


-- Create summary table
CREATE TABLE summary (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE summary IS 'Stores AI-generated summaries of user documents';
COMMENT ON COLUMN summary.summary_id IS 'Unique identifier for each summary';
COMMENT ON COLUMN summary.content IS 'Actual text content of the generated summary';


-- Create indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_summary_user_id ON summary(user_id);

COMMENT ON INDEX idx_documents_user_id IS 'Index for efficiently querying documents by user';
COMMENT ON INDEX idx_summary_user_id IS 'Index for efficiently querying summaries by user';


-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE summary ENABLE ROW LEVEL SECURITY;

-- RLS policies for users 
CREATE POLICY "Users can access their own profile" ON users
    FOR ALL USING (auth.uid() = id);

-- RLS policies for documents (CREATE, READ, DELETE)
CREATE POLICY "Users can view their own documents" ON documents
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can add their own documents" ON documents
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own documents" ON documents
    FOR DELETE USING (auth.uid() = user_id);

-- RLS policies for summaries (CREATE, READ, DELETE)
CREATE POLICY "Users can view their own summaries" ON summary
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can add their own summaries" ON summary
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own summaries" ON summary
    FOR DELETE USING (auth.uid() = user_id);


-- RPC functions for vector search
CREATE FUNCTION public.search_similar_documents(
    query_embedding VECTOR(1536), 
    user_id UUID, 
    match_count INTEGER DEFAULT 10
)
RETURNS TABLE(
    chunk_id UUID, 
    document_id UUID, 
    content TEXT, 
    title TEXT,
    score FLOAT
)
LANGUAGE SQL STABLE 
AS $$
SELECT
    chunk_id, 
    document_id, 
    content, 
    title, 
    1 - (embedding <=> query_embedding) AS score
FROM documents
WHERE 
    documents.user_id = search_similar_documents.user_id
ORDER BY score DESC 
LIMIT match_count; 
$$;

-- Grant appropriate permissions for the functions
GRANT EXECUTE ON FUNCTION public.search_similar_documents(VECTOR, UUID, INTEGER) TO authenticated;
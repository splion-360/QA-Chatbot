-- Drop the old documents table and recreate with new structure
DROP TABLE IF EXISTS documents CASCADE;

-- Create new documents table for metadata and full content
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    size BIGINT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector_store table for chunks and embeddings
CREATE TABLE vector_store (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(document_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_document_id ON documents(document_id);
CREATE INDEX idx_vector_store_document_id ON vector_store(document_id);

-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE vector_store ENABLE ROW LEVEL SECURITY;

-- RLS policies for documents
CREATE POLICY "Users can view their own documents" ON documents
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can add their own documents" ON documents
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own documents" ON documents
    FOR DELETE USING (auth.uid() = user_id);

-- RLS policies for vector_store
CREATE POLICY "Users can view their own chunks" ON vector_store
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM documents 
            WHERE documents.document_id = vector_store.document_id 
            AND documents.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add their own chunks" ON vector_store
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM documents 
            WHERE documents.document_id = vector_store.document_id 
            AND documents.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete their own chunks" ON vector_store
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM documents 
            WHERE documents.document_id = vector_store.document_id 
            AND documents.user_id = auth.uid()
        )
    );

-- Updated search function using vector_store table
CREATE OR REPLACE FUNCTION public.search_similar_documents(
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
    vs.chunk_id, 
    vs.document_id, 
    vs.content, 
    d.title,
    1 - (vs.embedding <=> query_embedding) AS score
FROM vector_store vs
JOIN documents d ON vs.document_id = d.document_id
WHERE 
    d.user_id = search_similar_documents.user_id
ORDER BY score DESC 
LIMIT match_count; 
$$;

GRANT EXECUTE ON FUNCTION public.search_similar_documents(VECTOR, UUID, INTEGER) TO authenticated;
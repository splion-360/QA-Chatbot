
DROP FUNCTION IF EXISTS public.search_similar_documents(VECTOR, UUID, INTEGER);

CREATE FUNCTION public.search_similar_documents(
    query_embedding VECTOR(1536), 
    user_id UUID, 
    match_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.0
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
FROM vector_store as vs
JOIN documents d ON vs.document_id = d.document_id
WHERE 
    d.user_id = search_similar_documents.user_id
ORDER BY score DESC 
LIMIT match_count; 
$$;

GRANT EXECUTE ON FUNCTION public.search_similar_documents(VECTOR, UUID, INTEGER, FLOAT) TO authenticated;